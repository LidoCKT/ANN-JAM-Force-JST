package io.github.annjam.timezone;

import android.app.Instrumentation;
import android.os.Bundle;
import android.os.SystemClock;
import android.system.Os;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Calendar;
import java.util.Date;
import java.util.TimeZone;
import java.util.concurrent.TimeUnit;

/**
 * Exercises production TimezonePolicy on Android, without LSPosed.
 * The libc check runs date in a child process with the native TZ value.
 * This does not exercise injected hooks or the target's Flutter engine.
 */
public final class SelfTestInstrumentation extends Instrumentation {
    private final StringBuilder report = new StringBuilder();
    private int passed;

    @Override
    public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override
    public void onStart() {
        Bundle result = new Bundle();
        TimeZone original = TimeZone.getDefault();
        String originalProperty = System.getProperty("user.timezone");
        String originalTz = Os.getenv("TZ");
        int code = -1;
        try {
            check("exact package", TimezonePolicy.isTarget("jp.annjam"));
            check("reject other apps", !TimezonePolicy.isTarget("jp.annjam.fake")
                    && !TimezonePolicy.isTarget("android")
                    && !TimezonePolicy.isTarget("io.github.annjam.timezone")
                    && !TimezonePolicy.isTarget(null));

            // Baseline: same instant is still November 5 in Shanghai.
            long instant = Instant.parse("2026-11-05T15:30:00Z").toEpochMilli();
            TimeZone.setDefault(TimeZone.getTimeZone("Asia/Shanghai"));
            check("UTC+8 baseline", format(instant).equals("2026-11-05T23:30:00+08:00"));

            long wallBefore = System.currentTimeMillis();
            long monoBefore = SystemClock.elapsedRealtime();
            TimezonePolicy.applyNativeEnvironment();
            TimezonePolicy.applyJavaDefaults();
            long wallDelta = System.currentTimeMillis() - wallBefore;
            long monoDelta = SystemClock.elapsedRealtime() - monoBefore;
            check("real clock unchanged", Math.abs(wallDelta - monoDelta) < 1000);
            check("native TZ environment", "Asia/Tokyo".equals(Os.getenv("TZ")));
            check("Java default", "Asia/Tokyo".equals(TimeZone.getDefault().getID()));
            check("Java offset", TimeZone.getDefault().getOffset(instant) == 32400000);
            check("ZoneId default", "Asia/Tokyo".equals(ZoneId.systemDefault().getId()));
            check("cross midnight", format(instant).equals("2026-11-06T00:30:00+09:00"));

            Calendar calendar = Calendar.getInstance();
            calendar.setTimeInMillis(instant);
            check("Calendar local date", calendar.get(Calendar.DAY_OF_MONTH) == 6
                    && calendar.get(Calendar.HOUR_OF_DAY) == 0);
            android.icu.text.SimpleDateFormat icu =
                    new android.icu.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX");
            check("ICU default cache", icu.format(new Date(instant))
                    .equals("2026-11-06T00:30:00+09:00"));

            TimeZone zone = TimezonePolicy.newJavaZone();
            zone.setRawOffset(0);
            check("mutable instance isolation",
                    TimezonePolicy.newJavaZone().getOffset(instant) == 32400000);
            TimezonePolicy.applyNativeEnvironment();
            TimezonePolicy.applyJavaDefaults();
            check("idempotent apply", format(instant).equals("2026-11-06T00:30:00+09:00"));

            ProcessBuilder builder = new ProcessBuilder("/system/bin/date", "-d",
                    "@" + instant / 1000, "+%Y-%m-%dT%H:%M:%S %z");
            // Explicitly use libc's environment value rather than Java's
            // possibly cached ProcessEnvironment copy inherited from zygote.
            builder.environment().put("TZ", Os.getenv("TZ"));
            builder.redirectErrorStream(true);
            Process child = builder.start();
            if (!child.waitFor(10, TimeUnit.SECONDS)) {
                child.destroyForcibly();
                throw new AssertionError("native date timeout");
            }
            String nativeResult;
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(child.getInputStream()))) {
                nativeResult = reader.readLine();
            }
            check("bionic child date", child.exitValue() == 0
                    && "2026-11-06T00:30:00 +0900".equals(nativeResult));
            report.append("native date: ").append(nativeResult).append('\n');
            result.putBoolean("passed", true);
        } catch (Throwable failure) {
            code = 0;
            report.append("FAILED: ").append(failure).append('\n');
            result.putBoolean("passed", false);
        } finally {
            try {
                if (originalTz == null) Os.unsetenv("TZ");
                else Os.setenv("TZ", originalTz, true);
                TimeZone.setDefault(original);
                if (originalProperty == null) System.clearProperty("user.timezone");
                else System.setProperty("user.timezone", originalProperty);
            } catch (Exception error) {
                code = 0;
                result.putBoolean("passed", false);
                report.append("FAILED restoring test process: ").append(error).append('\n');
            }
        }
        result.putInt("checksPassed", passed);
        result.putString("stream", "\n" + report);
        finish(code, result);
    }

    private static String format(long instant) {
        return DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX")
                .withZone(ZoneId.systemDefault()).format(Instant.ofEpochMilli(instant));
    }

    private void check(String name, boolean condition) {
        if (!condition) throw new AssertionError(name);
        passed++;
        report.append("PASS ").append(name).append('\n');
    }
}
