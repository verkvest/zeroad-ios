# zeroad-ios — прототип порта 0 A.D. на iOS

Экспериментальный порт стратегии [0 A.D.](https://play0ad.com) (Wildfire Games) на iPhone/iPad.
Исходники движка **не копируются** в этот репозиторий: скрипт `scripts/fetch-0ad.sh` скачивает
зафиксированный тег **v0.28.0** (`a2cae4d6…`) с https://gitea.wildfiregames.com/0ad/0ad (только код, без арта),
а наши изменения лежат отдельными патчами в `patches/`.

## Архитектура

```
scripts/fetch-0ad.sh          sparse-клон 0ad v0.28.0 (source, libraries, build) + проверка коммита
scripts/apply-0ad-patches.sh  кладёт touch/ в source/ps и применяет patches/0ad/*.patch
ios/env.sh                    кросс-окружение: iphonesimulator|iphoneos, arm64, iOS 15.0
ios/build-ios-deps.sh         статические зависимости: SDL2, libpng, freetype, ogg/vorbis, fmt, enet,
                              libsodium, boost (headers), OpenAL-soft (CoreAudio), curl (SecureTransport), ICU
                              (zlib, iconv, libxml2 — из iOS SDK)
ios/build-spidermonkey-ios.sh SpiderMonkey 128 (mozjs-128.13.0, как в 0ad) БЕЗ JIT:
                              --enable-portable-baseline-interp (iOS запрещает JIT в сторонних приложениях)
ios/build-engine.sh           premake 0ad (gmake, --gles, без atlas/lobby/nvtt/tests) с iOS-флагами компилятора;
                              make -k, собирает полный лог и сводку ошибок
touch/                        TouchGestures — независимый от движка распознаватель жестов + unit-тесты
patches/0ad/0001-ios-touch-input.patch
                              OS_IOS в os.h; TouchInput.cpp переписан на TouchGestures; камера не отключается
touchdemo/                    SDL2-приложение ZeroADTouch.app — демо жестов с самотестом в симуляторе
.github/workflows/ios-build.yml      CI: тесты жестов → deps (sim+device) → SpiderMonkey → touchdemo .app
                                     (+ запуск в iOS Simulator, скриншот) → engine (экспериментально)
.github/workflows/ios-testflight.yml ручной запуск: подпись через App Store Connect API key и загрузка в TestFlight
```

### Жесты (движок и демо)

| Жест | Действие в игре |
|---|---|
| тап одним пальцем | левый клик (выбор юнита/кнопки) |
| удержание + ведение | рамка выделения (drag левой кнопкой) |
| тап двумя пальцами | правый клик (приказ: идти/атаковать/собирать) |
| щипок (pinch) | зум камеры (через синтетический mouse wheel) |
| ведение двумя пальцами | перемещение камеры «за землю»; в меню — прокрутка |

## Что работает (проверено в CI)

- unit-тесты распознавателя жестов (Linux);
- патч 0ad применяется к v0.28.0;
- все сторонние библиотеки собираются статически для iOS Simulator и iPhone (arm64);
- SpiderMonkey 128 собирается для iOS Simulator в режиме интерпретатора (без JIT);
- `ZeroADTouch.app` собирается для симулятора и устройства; в iOS Simulator проходит самотест
  (`TOUCHDEMO SELFTEST PASS`: тап, двухпальцевый тап, pan, pinch, drag), скриншот в артефакте;
- workflow TestFlight готов, без секретов корректно пропускается (зелёный).

## Что не работает / блокеры

0. **CI остановлен биллингом GitHub** (с 24.10.2026 00:13 Europe/Madrid): macOS-задачи не стартуют —
   «recent account payments have failed or your spending limit needs to be increased». Нужно поправить оплату/лимит
   в Settings → Billing & plans аккаунта verkvest (или сделать репозиторий публичным — тогда macOS-минуты бесплатны).
1. **Движок (pyrogenesis) под iOS Simulator компилируется полностью** (505 объектных файлов, 0 ошибок компиляции,
   патч `patches/0ad/0002-ios-build.patch`), но **ещё не слинкован**: в последнем прогоне оставались неразрешённые
   символы mfbt (double_conversion, SHA1Sum, RandomUint64…), `startNewAtlasProcess` и одна инстанциация fmt —
   исправления (mfbt в `libmozjs128-glue.a`, `sysdep/os/ios/ios_stubs.cpp`) запушены, но не проверены из-за биллинга.
   Сборка движка для устройства (iphoneos) и SpiderMonkey для iphoneos ещё не добавлены в CI.
   Job `engine` (continue-on-error)
   компилирует его, пытается упаковать `Pyrogenesis.app` с мини-модом `mod` и запустить в симуляторе
   (`scripts/package-engine-app.sh`, `scripts/sim-launch.py`), лог — артефакт `engine-iphonesimulator-log`.
   Оставшиеся задачи:
   - AppKit/FSEvents уже отключены для iOS (заглушки dir_watch/atlas), но нужна проверка путей бандла,
     курсора и сведений о системе в рантайме;
   - premake-скрипты 0ad ориентированы на macOS (ConsoleApp, `-framework OpenGL/Cocoa`); для .app нужен
     отдельный таргет (Xcode/CMake) с Info.plist и iOS-фреймворками;
   - рендер: в 0.28 есть GL-бэкенд с `--gles` (OpenGL ES устарел на iOS, но работает) и Vulkan-бэкенд;
     правильный путь — Vulkan через MoltenVK, его нужно собрать под iOS;
   - SpiderMonkey без JIT — ИИ и симуляция на JS будут заметно медленнее (оценить на устройстве).
2. **Данные игры (≈1–2 ГБ арта)** не входят в репозиторий; нужна упаковка `public.zip` в бандл или
   загрузка при первом запуске, плюс предконвертация моделей/текстур (на iOS нет FCollada/NVTT в рантайме).
3. **UI под палец**: интерфейс 0 A.D. рассчитан на мышь и клавиатуру (горячие клавиши, мелкие кнопки).
4. **Подпись/TestFlight**: секреты `APPSTORE_API_KEY_P8`, `APPSTORE_API_KEY_ID`, `APPSTORE_API_ISSUER_ID`
   владелец добавляет сам (Settings → Secrets → Actions). App ID `es.verkvest.zeroad` должен существовать
   или создаться при подписи (`-allowProvisioningUpdates`).
5. Репозиторий приватный: бесплатные минуты macOS-раннеров ограничены (macOS-минуты считаются ×10).

## Следующие шаги и оценки

| Шаг | Оценка |
|---|---|
| Довести компиляцию движка: sysdep/os/ios, исправления premake, линковка | 3–5 дней |
| iOS .app-таргет движка (CMake/Xcode), запуск главного меню в симуляторе на mod `mod` | 2–4 дня |
| MoltenVK/Vulkan или GLES-рендер на устройстве, отладка шейдеров | 3–7 дней |
| Упаковка данных `public`, предконвертация кэша, запуск матча | 3–5 дней |
| Адаптация UI под тач (крупные кнопки, контекстное меню вместо горячих клавиш) | 1–3 недели |
| Производительность (без JIT), память, энергопотребление | 1–2 недели |
| **Первая сборка в TestFlight с реальной игрой** | **≈ 3–6 недель** |

TestFlight-сборку уже сейчас можно сделать из `touchdemo` (после добавления секретов) — это проверит подпись
и загрузку, но это ещё не игра.

## Лицензия и условия публикации

- Код 0 A.D. распространяется под **GPL v2 (или новее)**, арт — под **CC BY-SA 3.0**. Наш код и патчи
  в этом репозитории также под GPL v2+.
- Приложение в App Store должно быть **бесплатным**; перед релизом **исходники (включая все патчи и
  скрипты сборки) должны быть опубликованы** — репозиторий нужно сделать публичным.
- Обязательно указывать авторство: «0 A.D. © Wildfire Games, https://play0ad.com», в описании
  приложения и в экране «О программе». Название и логотип 0 A.D. — товарные знаки Wildfire Games;
  для публикации под этим именем лучше согласовать с ними.
- Требования App Store (запрет на доп. ограничения пользователей) исторически конфликтуют с GPL —
  перед релизом стоит согласовать распространение с Wildfire Games.
