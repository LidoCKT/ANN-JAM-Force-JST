package io.github.annjam.timezone;

import android.app.Application;
import android.content.Context;
import android.system.Os;
import android.util.Log;
import java.time.ZoneId;
import java.util.TimeZone;
import java.util.concurrent.atomic.AtomicBoolean;
import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

public final class TimezoneModule implements IXposedHookLoadPackage {
    private static final String TAG = "ANNJAM-TZ";
    private static final AtomicBoolean INSTALLED = new AtomicBoolean();

    @Override
    public void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) {
        // Keep this guard even when the user selects extra apps in LSPosed.
        // Deliberately no zygote hook: siblings must inherit their real timezone.
        if (!TimezonePolicy.isTarget(lpparam.packageName)
                || !INSTALLED.compareAndSet(false, true)) {
            return;
        }

        applyDefaults("loadPackage", lpparam.processName);
        installJavaHooks();
        installEnvironmentHooks();
        installIcuHooks();

        // Reassert defaults before the target Application's attachBaseContext
        // and onCreate, where Flutter engines and app plugins may be created.
        try {
            XposedHelpers.findAndHookMethod(Application.class, "attach", Context.class,
                    new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            applyDefaults("Application.attach", lpparam.processName);
                        }
                    });
        } catch (Throwable error) {
            reportFailure("Application.attach hook", error);
        }
    }

    private static void installJavaHooks() {
        try {
            XposedHelpers.findAndHookMethod(TimeZone.class, "getDefault",
                    new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            param.setResult(TimezonePolicy.newJavaZone());
                        }
                    });
            // Keep Android's normal cache/ICU invalidation behavior, replacing
            // only the timezone argument, including reset-to-system (null).
            XposedHelpers.findAndHookMethod(TimeZone.class, "setDefault", TimeZone.class,
                    new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            param.args[0] = TimezonePolicy.newJavaZone();
                        }
                    });
        } catch (Throwable error) {
            reportFailure("java.util.TimeZone hooks", error);
        }
        try {
            XposedHelpers.findAndHookMethod(ZoneId.class, "systemDefault",
                    new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            param.setResult(ZoneId.of(TimezonePolicy.ZONE_ID));
                        }
                    });
        } catch (Throwable error) {
            reportFailure("java.time.ZoneId hook", error);
        }
    }

    private static void installEnvironmentHooks() {
        try {
            XposedHelpers.findAndHookMethod(Os.class, "setenv",
                    String.class, String.class, boolean.class, new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            if ("TZ".equals(param.args[0])) {
                                param.args[1] = TimezonePolicy.ZONE_ID;
                                param.args[2] = true;
                            }
                        }
                    });
            XposedHelpers.findAndHookMethod(Os.class, "unsetenv",
                    String.class, new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            if ("TZ".equals(param.args[0])) {
                                param.setResult(null);
                            }
                        }
                    });
        } catch (Throwable error) {
            reportFailure("TZ environment hooks", error);
        }
    }

    private static void installIcuHooks() {
        try {
            XposedHelpers.findAndHookMethod(android.icu.util.TimeZone.class, "getDefault",
                    new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            param.setResult(android.icu.util.TimeZone.getTimeZone(
                                    TimezonePolicy.ZONE_ID));
                        }
                    });
            XposedHelpers.findAndHookMethod(android.icu.util.TimeZone.class, "setDefault",
                    android.icu.util.TimeZone.class, new XC_MethodHook() {
                        @Override
                        protected void beforeHookedMethod(MethodHookParam param) {
                            param.args[0] = android.icu.util.TimeZone.getTimeZone(
                                    TimezonePolicy.ZONE_ID);
                        }
                    });
        } catch (Throwable error) {
            reportFailure("android.icu.util.TimeZone hooks", error);
        }
    }

    private static void applyDefaults(String stage, String processName) {
        boolean nativeEnvironmentOk = false;
        try {
            TimezonePolicy.applyNativeEnvironment();
            nativeEnvironmentOk = TimezonePolicy.ZONE_ID.equals(Os.getenv("TZ"));
        } catch (Throwable error) {
            reportFailure("libc TZ environment", error);
        }
        try {
            TimezonePolicy.applyJavaDefaults();
        } catch (Throwable error) {
            reportFailure("Java default timezone", error);
        }
        // Android's TimeZone.setDefault invalidates ICU's default cache.
        // ICU's hidden setDefault is hooked above when available; calling it
        // directly would require hidden-API reflection and is unnecessary.
        String message = TAG + " " + stage + " process=" + processName
                + " java=" + TimeZone.getDefault().getID()
                + " offsetMillis=" + TimeZone.getDefault().getOffset(System.currentTimeMillis())
                + " libcTZ=" + Os.getenv("TZ")
                + " environmentOK=" + nativeEnvironmentOk;
        XposedBridge.log(message);
        Log.i(TAG, message);
    }

    private static void reportFailure(String operation, Throwable error) {
        String message = TAG + " FAILED " + operation + ": " + error;
        XposedBridge.log(message);
        Log.e(TAG, message, error);
    }
}
