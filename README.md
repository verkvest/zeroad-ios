# zeroad-ios — порт 0 A.D. на iOS

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
| тап одним пальцем | выбор юнита/здания, кнопки GUI |
| тап при выбранных своих юнитах (по земле, врагу, ресурсу) | приказ: идти / атаковать / собирать / строить (мод `ios`) |
| двойной тап | выбрать всех юнитов этого типа на экране |
| удержание ≈0,55 с (long-press) | правый клик (приказ; гарнизон/ремонт по своему зданию) |
| ведение одним пальцем | рамка выделения |
| тап двумя пальцами | правый клик |
| ведение двумя пальцами | камера «за землю»; в меню — прокрутка |
| щипок (pinch) | зум камеры |

## Данные игры

Официальные данные 0.28.0 (`public.zip` 3,5 ГБ) пережаты `scripts/pack-mobile-data.py` до ≈600 МБ
(урезаны верхние mip-уровни DDS, музыка Vorbis q0, 12 карт для схватки, без сценариев и SPIR-V) и лежат
в релизе [`mobile-data-0.28.0-v1`](https://github.com/verkvest/zeroad-ios/releases/tag/mobile-data-0.28.0-v1).
`scripts/package-engine-app.sh` скачивает их, проверяет SHA-256 и кладёт в бандл вместе с `mod.zip`,
модом `ios` (сенсорные приказы, `ios/make-ios-mod.py`) и `CREDITS.txt`. Настройки по умолчанию для iPhone
(низкая графика, Retina, без edge-scroll, автомасштаб GUI) — `ios/ios-config.py`. Только альбомная ориентация.

## Что работает (проверено в CI, iOS Simulator)

- движок, SpiderMonkey 128 без JIT и зависимости собираются для симулятора и iPhone;
- главное меню 0 A.D. отображается (`shots/m1-mainmenu/`);
- схватка (Acropolis Bay, 1 ИИ Petra) запускается и рендерится: ландшафт, здания, юниты, мини-карта
  (`shots/m2-skirmish/`); сценарий сенсорного самотеста (`-conf=ios.touchtest:true`) прогоняет рамку,
  приказ тапом, long-press, pan, pinch и двойной тап;
- TestFlight: тег `testflight-engine-N` → подпись через App Store Connect API key → загрузка.

## Ограничения

1. Производительность на реальном iPhone без JIT (ИИ на JS) не измерена — нужен тест на устройстве.
2. Интерфейс 0 A.D. остаётся «мышиным»: горячих клавиш нет, мелкие кнопки (масштаб GUI ≥1.0).
3. Размер .ipa ≈ 700 МБ (больше лимита загрузки по сотовой сети — скачивать по Wi-Fi).

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
