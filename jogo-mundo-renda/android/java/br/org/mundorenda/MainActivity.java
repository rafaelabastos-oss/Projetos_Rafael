package br.org.mundorenda;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Vibrator;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;

/**
 * Mundo Renda: hospeda o jogo (HTML5 Canvas) num WebView em tela cheia.
 * Os arquivos do jogo ficam em assets/www e rodam 100% offline.
 * O salvamento é feito em arquivos privados do app (ponte AndroidBridge).
 */
public class MainActivity extends Activity {

    private static final String START_URL = "file:///android_asset/www/index.html";

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_FULLSCREEN);

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#14261f"));
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);

        web.addJavascriptInterface(new Bridge(), "AndroidBridge");
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            @SuppressWarnings("deprecation")
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("file:///android_asset/")) return false;
                Uri u = Uri.parse(url);
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                } catch (Exception e) {
                    // sem navegador: ignora
                }
                return true;
            }
        });

        setContentView(web);
        hideSystemUi();
        web.loadUrl(START_URL);
    }

    @SuppressWarnings("deprecation")
    private void hideSystemUi() {
        web.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUi();
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        if (web == null) {
            super.onBackPressed();
            return;
        }
        web.evaluateJavascript("(window.onAndroidBack && window.onAndroidBack()) ? 'h' : 'n'",
                new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        if (value == null || !value.contains("h")) finish();
                    }
                });
    }

    @Override
    protected void onPause() {
        if (web != null) {
            web.evaluateJavascript("window.onAppPause && window.onAppPause()", null);
            web.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) {
            web.onResume();
            hideSystemUi();
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.removeJavascriptInterface("AndroidBridge");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    /** Ponte JavaScript: salvar/carregar em arquivos privados do app, vibrar, compartilhar e sair. */
    private class Bridge {
        private File dir() {
            File d = new File(getFilesDir(), "saves");
            if (!d.exists()) d.mkdirs();
            return d;
        }

        private File file(String key) {
            String safe = key == null ? "x" : key.replaceAll("[^A-Za-z0-9_\\-]", "_");
            return new File(dir(), safe + ".json");
        }

        @JavascriptInterface
        public String load(String key) {
            File f = file(key);
            if (!f.exists()) return null;
            FileInputStream in = null;
            try {
                in = new FileInputStream(f);
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                return new String(out.toByteArray(), "UTF-8");
            } catch (Exception e) {
                return null;
            } finally {
                try { if (in != null) in.close(); } catch (Exception ignored) { }
            }
        }

        @JavascriptInterface
        public boolean save(String key, String data) {
            File f = file(key);
            File tmp = new File(f.getPath() + ".tmp");
            FileOutputStream out = null;
            try {
                out = new FileOutputStream(tmp);
                out.write(data.getBytes("UTF-8"));
                out.getFD().sync();
                out.close();
                out = null;
                if (f.exists() && !f.delete()) return false;
                return tmp.renameTo(f);
            } catch (Exception e) {
                return false;
            } finally {
                try { if (out != null) out.close(); } catch (Exception ignored) { }
            }
        }

        @JavascriptInterface
        public void remove(String key) {
            File f = file(key);
            if (f.exists()) f.delete();
        }

        @JavascriptInterface
        public void vibrate(int ms) {
            try {
                Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null) v.vibrate(Math.max(5, Math.min(ms, 400)));
            } catch (Exception ignored) { }
        }

        @JavascriptInterface
        public void share(final String text) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Intent i = new Intent(Intent.ACTION_SEND);
                        i.setType("text/plain");
                        i.putExtra(Intent.EXTRA_TEXT, text);
                        startActivity(Intent.createChooser(i, "Compartilhar projeto"));
                    } catch (Exception ignored) { }
                }
            });
        }

        @JavascriptInterface
        public String version() {
            return "1.0.0 (Android " + Build.VERSION.RELEASE + ")";
        }

        @JavascriptInterface
        public void exitApp() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    finish();
                }
            });
        }
    }
}
