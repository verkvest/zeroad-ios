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
- SpiderMonkey 128 (без JIT) собирается и для устройства (iphoneos);
- **движок pyrogenesis компилируется и линкуется** для iOS Simulator и iPhone (arm64): 506 объектных файлов,
  0 ошибок, 0 неразрешённых символов (`patches/0ad/0002-ios-build.patch`, `libmozjs128-glue.a`);
- `Pyrogenesis.app` (движок + официальный `mod.zip` из релизного архива 0.28.0, без арта игры) **запускается
  в iOS Simulator**: VFS, конфиг, логи, SDL2, OpenAL и контекст OpenGL ES 2.0 инициализируются; падал на
  проверке десктопных GL-расширений — исправлено `0003-gles-device-check.patch` (проверяется);
- TestFlight-конвейер: архив → экспорт с облачной подписью App Store (через API key) работает и для
  touch-демо, и для движка (`.ipa` ≈ 89 МБ). Загрузка упирается только в отсутствие записи приложения
  в App Store Connect (см. блокеры). Теги `testflight-touchdemo-N` / `testflight-engine-N` запускают загрузку.

## Что не работает / блокеры

1. **Нет записи приложения в App Store Connect** для `es.verkvest.zeroad` (altool: «Cannot determine the Apple ID
   from Bundle ID»). App Store Connect API не умеет создавать приложения — только веб: Apps → «+» → New App,
   iOS, имя «0 A.D. Verkvest», язык English, Bundle ID `es.verkvest.zeroad`, SKU `zeroad-ios`.
   После этого — повторить тег `testflight-*`.
2. **Рендер**: дальше по пути запуска — GLSL-шейдеры 0ad под GLES (на Android-ветке они частично есть),
   OpenGL ES на iOS устарел; правильный путь — Vulkan-бэкенд через MoltenVK.
3. SpiderMonkey без JIT — ИИ и симуляция на JS будут заметно медленнее (оценить на устройстве).
4. **Данные игры (`public.zip` ≈ 3,5 ГБ)** не входят в бандл; нужна загрузка при первом запуске или
   On-Demand Resources, плюс предконвертация моделей/текстур (на iOS нет FCollada/NVTT в рантайме).
5. **UI под палец**: интерфейс 0 A.D. рассчитан на мышь и клавиатуру (горячие клавиши, мелкие кнопки).

## Следующие шаги и оценки

| Шаг | Оценка |
|---|---|
| ~~Компиляция и линковка движка~~ | готово |
| Главное меню в симуляторе на моде `mod` (GLES-шейдеры, пути бандла) | 2–4 дня |
| MoltenVK/Vulkan или GLES-рендер на устройстве, отладка шейдеров | 3–7 дней |
| Упаковка данных `public`, предконвертация кэша, запуск матча | 3–5 дней |
| Адаптация UI под тач (крупные кнопки, контекстное меню вместо горячих клавиш) | 1–3 недели |
| Производительность (без JIT), память, энергопотребление | 1–2 недели |
| **Играбельная сборка в TestFlight с реальной игрой** | **≈ 3–5 недель** |

TestFlight-сборки touch-демо и движка (пока без игровых данных) готовы к загрузке сразу после создания
записи приложения в App Store Connect.

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
