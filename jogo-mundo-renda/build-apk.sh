#!/usr/bin/env bash
# Mundo Renda - gera o APK Android sem Android Studio/Gradle.
# Requisitos (Debian/Ubuntu): sudo apt-get install -y aapt apksigner zipalign dalvik-exchange android-sdk-platform-23 default-jdk zip
# Uso: ./build-apk.sh            -> dist/MundoRenda.apk
#      VERSION_CODE=2 VERSION_NAME=1.1.0 ./build-apk.sh
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_SDK:-/usr/lib/android-sdk}"
PLATFORM="${ANDROID_JAR:-$SDK/platforms/android-23/android.jar}"
VERSION_CODE="${VERSION_CODE:-1}"
VERSION_NAME="${VERSION_NAME:-1.0.0}"
MIN_SDK=21
TARGET_SDK=34
APP=android
OUT=build
APK_NAME="${APK_NAME:-MundoRenda.apk}"
KEYSTORE="${KEYSTORE:-keystore/mundorenda-debug.jks}"
KS_PASS="${KS_PASS:-android}"
KEY_ALIAS="${KEY_ALIAS:-mundorenda}"

for tool in aapt2 javac dalvik-exchange zipalign apksigner zip keytool; do
  command -v "$tool" >/dev/null || { echo "Falta a ferramenta: $tool" >&2; exit 1; }
done
[ -f "$PLATFORM" ] || { echo "android.jar não encontrado em $PLATFORM" >&2; exit 1; }

echo "==> Limpando"
rm -rf "$OUT"; mkdir -p "$OUT"/{gen,classes,dex} dist

echo "==> Verificando o JavaScript"
if command -v node >/dev/null; then
  for f in "$APP"/assets/www/js/*.js; do node --check "$f"; done
fi

echo "==> Compilando recursos (aapt2)"
aapt2 compile --dir "$APP/res" -o "$OUT/res.zip"
aapt2 link -o "$OUT/base.apk" -I "$PLATFORM" --manifest "$APP/AndroidManifest.xml" \
  -A "$APP/assets" --java "$OUT/gen" \
  --min-sdk-version "$MIN_SDK" --target-sdk-version "$TARGET_SDK" \
  --version-code "$VERSION_CODE" --version-name "$VERSION_NAME" \
  --auto-add-overlay "$OUT/res.zip"

echo "==> Compilando Java"
javac -source 8 -target 8 -bootclasspath "$PLATFORM" -Xlint:-options -encoding UTF-8 \
  -d "$OUT/classes" $(find "$APP/java" "$OUT/gen" -name '*.java')

echo "==> Gerando DEX"
dalvik-exchange --dex --min-sdk-version="$MIN_SDK" --output="$OUT/dex/classes.dex" "$OUT/classes"

echo "==> Empacotando"
cp "$OUT/base.apk" "$OUT/unaligned.apk"
(cd "$OUT/dex" && zip -q -X ../unaligned.apk classes.dex)
zipalign -f -p 4 "$OUT/unaligned.apk" "$OUT/aligned.apk"

if [ ! -f "$KEYSTORE" ]; then
  echo "==> Criando chave de assinatura de testes em $KEYSTORE"
  mkdir -p "$(dirname "$KEYSTORE")"
  keytool -genkeypair -keystore "$KEYSTORE" -storepass "$KS_PASS" -keypass "$KS_PASS" -alias "$KEY_ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Mundo Renda, OU=Jogo, O=Mundo Renda, C=BR"
fi

echo "==> Assinando (v1 + v2 + v3)"
apksigner sign --ks "$KEYSTORE" --ks-pass "pass:$KS_PASS" --ks-key-alias "$KEY_ALIAS" --key-pass "pass:$KS_PASS" \
  --out "dist/$APK_NAME" "$OUT/aligned.apk"
apksigner verify --verbose "dist/$APK_NAME" | grep -E "Verifies|v2|v3" || true
rm -f "dist/$APK_NAME.idsig"

echo "==> Pronto: dist/$APK_NAME ($(du -h "dist/$APK_NAME" | cut -f1))"
