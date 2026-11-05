package io.github.annjam.timezone;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.graphics.Color;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/** Instructions only. The module does not inject into its own launcher process. */
public final class MainActivity extends Activity {
    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        int padding = Math.round(24 * getResources().getDisplayMetrics().density);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(padding, padding * 2, padding, padding);
        content.setBackgroundColor(Color.rgb(246, 248, 252));

        TextView title = new TextView(this);
        title.setText("ANN JAM 日本时区");
        title.setTextSize(26);
        title.setTextColor(Color.rgb(24, 43, 76));
        content.addView(title);

        TextView instructions = new TextView(this);
        instructions.setTextSize(17);
        instructions.setTextColor(Color.rgb(40, 50, 65));
        instructions.setPadding(0, padding, 0, padding);
        instructions.setText(
                "1. 在 LSPosed 中启用本模块。\n\n"
                + "2. 作用域只勾选 ANN JAM（jp.annjam）。\n\n"
                + "3. 保持手机系统为你日常使用的时区。\n\n"
                + "4. 在系统设置中强制停止 ANN JAM，然后重新打开。"
                + "如果未生效，重启手机再试。\n\n"
                + "模块目标：让 ANN JAM 的 Java、ICU 和 Flutter 本地时区"
                + "统一使用 Asia/Tokyo（UTC+9）。\n\n"
                + "安装成功不代表已注入；是否启用请以 LSPosed 管理器为准。"
                + "本页面不会读取或猜测模块激活状态。\n\n"
                + "排查日志：在 LSPosed 日志中搜索 ANNJAM-TZ。"
                + "正常应看到 java=Asia/Tokyo、offsetMillis=32400000、"
                + "libcTZ=Asia/Tokyo、environmentOK=true。\n\n"
                + "恢复：停用本模块并强制停止 ANN JAM，再重新打开。");
        content.addView(instructions);

        Button open = new Button(this);
        open.setText("打开 ANN JAM");
        open.setOnClickListener(view -> {
            Intent launch = getPackageManager().getLaunchIntentForPackage(
                    TimezonePolicy.TARGET_PACKAGE);
            if (launch != null) {
                try {
                    startActivity(launch);
                } catch (RuntimeException error) {
                    Toast.makeText(this, "无法打开 ANN JAM，请从桌面启动。",
                            Toast.LENGTH_LONG).show();
                }
            } else {
                Toast.makeText(this, "未找到 ANN JAM，请确认安装在当前用户中。",
                        Toast.LENGTH_LONG).show();
            }
        });
        content.addView(open);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(content);
        setContentView(scroll);
    }
}
