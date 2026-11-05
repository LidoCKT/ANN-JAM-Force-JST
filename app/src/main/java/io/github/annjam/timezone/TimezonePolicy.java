package io.github.annjam.timezone;

import android.system.ErrnoException;
import android.system.Os;
import java.util.TimeZone;

/** All changes made here belong to the current app process, never to the system. */
public final class TimezonePolicy {
    public static final String TARGET_PACKAGE = "jp.annjam";
    public static final String ZONE_ID = "Asia/Tokyo";

    private TimezonePolicy() {}

    public static boolean isTarget(String packageName) {
        return TARGET_PACKAGE.equals(packageName);
    }

    public static TimeZone newJavaZone() {
        // Always return a new instance: TimeZone is mutable.
        return TimeZone.getTimeZone(ZONE_ID);
    }

    public static void applyNativeEnvironment() throws ErrnoException {
        // Os.setenv writes libc's actual environment; System.setProperty does not.
        // On Android O+, bionic localtime_r refreshes TZ itself. Dart uses that
        // function for its local timezone name and UTC offset.
        Os.setenv("TZ", ZONE_ID, true);
    }

    public static void applyJavaDefaults() {
        System.setProperty("user.timezone", ZONE_ID);
        TimeZone.setDefault(newJavaZone());
    }
}
