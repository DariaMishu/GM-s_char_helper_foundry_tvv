# Foundry VTT NPC Builder

Streamlit-приложение для быстрой сборки JSON-файла мастер-персонажа (NPC) для
[Foundry VTT](https://foundryvtt.com/) с системой **dnd5e**. Готовый файл
импортируется в Foundry через `Sidebar → Actors → Import`.

Тестировалось со связкой Foundry VTT core **13.x** и dnd5e **5.x** (правила 2014).

## Возможности

- **Имя, раса, класс** — обязательные поля. В зависимости от чекбокса «Монстр»
  третьим обязательным полем становится **КО** (CR 0…30 из DMG, с XP) или
  **уровень персонажа** (1…20 по правилам PHB).
- **Два режима скейлинга — КО и уровень**. Оба режима автоматически
  предлагают характеристики, КД, HP и слоты заклинаний на основе сочетания
  «класс + ранг»:
  - **Режим КО** (`cr_scaling.json`) — значения HP откалиброваны по реальному
    бестиарию Monster Manual (DMG-таблица занижена/завышена в среднем в 1.5–2 раза
    относительно фактических монстров, см. [анализ Blog of Holding](https://www.blogofholding.com/?p=7283)).
    Для каждой строки сохранён комментарий с примерами монстров и средним HP.
  - **Режим уровня** (`level_scaling.json`) — HP считается по PHB (max d8 + CON
    на 1-м уровне, далее +средний d8 + CON), AC растёт 13 → 18, ASI отражены
    на уровнях 4 / 8 / 12 / 16 / 19, бонус мастерства +2 → +6, слоты
    заклинателя берутся напрямую от уровня (full / half / third / pact).
  - Профиль `[primary, secondary, tertiary, dump]` распределяется по приоритету
    характеристик класса (волшебник → большой интеллект и низкая сила;
    варвар → сила и телосложение; жрец → мудрость; и т.д.).
  - HP = базовый HP режима × множитель класса (`hp_multiplier`,
    d6=0.80 / d8=1.00 / d10=1.15 / d12=1.30).
  - КД = базовый КД режима + модификатор класса (`ac_modifier`),
    но не ниже базового КД самого класса.
  - Для NPC, заданных уровнем, поле `system.details.cr` заполняется
    приближённо (уровень → КО), чтобы корректно работал бонус мастерства
    в Foundry.
- **Скорость от расы** — `system.attributes.movement.walk` берётся из `races.json`
  (дварф 25, кентавр 40, лесной эльф 35 и т.д.).
- **Тип существа и подтип** — чекбокс «Монстр» в блоке «Основное» переключает режим.
  Если выбран «Гуманоид» — остаётся обычный выбор расы. Для остальных типов
  (нежить, исчадие, дракон…) вместо расы вводится свободный текстовый подтип.
  Соответствует `system.details.type.value` / `system.details.type.subtype`.
- **Размер существа** — выбирается из стандартной сетки D&D (Tiny…Gargantuan)
  и автоматически ставит `system.traits.size`, а также размер токена в клетках
  (`prototypeToken.width`/`height`): tiny 0.5×0.5, sm/med 1×1, lg 2×2, huge 3×3, grg 4×4.
- **Ручное переопределение** любого рекомендованного значения прямо в интерфейсе.
- **Устойчивости / невосприимчивости / уязвимости** к типам урона.
- **Невосприимчивости к состояниям**.
- **Биография** — необязательное поле, попадает в `system.details.biography.value`.
- **Отношение к игрокам** — дружелюбный / нейтральный / враждебный (`prototypeToken.disposition`).
- **Загрузка портрета и токена** — изображения встраиваются в JSON как `data:` URI,
  файл самодостаточен. Рядом с полями загрузки выводятся миниатюры-превью
  (~25% ширины контента), чтобы сразу проверить, что подгрузилось нужное изображение.

## Структура репозитория

```
foundry-npc-builder/
├── app.py                       # Streamlit-приложение
├── data/
│   ├── races.json               # Расы: тип существа, размер, скорость
│   ├── classes.json             # Классы: base_ac, ac_modifier, hp_multiplier,
│   │                            #         ability_priority, caster_type
│   ├── damage_types.json        # Типы урона и состояния D&D 5e
│   ├── creature_types.json      # Типы существ (гуманоид, нежить, исчадие и т.д.)
│   ├── sizes.json               # Размеры существа и размер токена (в клетках)
│   ├── cr_table.json            # Таблица класса опасности (CR 0–30)
│   ├── cr_scaling.json          # Скейлинг HP/AC/хар-к/слотов по CR (откалибровано по MM)
│   └── level_scaling.json       # Скейлинг HP/AC/хар-к/слотов по уровню 1–20 (PHB)
├── templates/
│   └── npc_template.json        # Базовая структура NPC Actor
├── .streamlit/config.toml       # Настройки темы и upload-лимита
├── requirements.txt
├── LICENSE
└── README.md
```

## Установка и запуск

### Быстрый способ — двойной клик

В корне репозитория лежат готовые запускаторы:

- **Windows** — дважды щёлкните `run.bat`.
- **macOS / Linux** — выполните в терминале `./run.sh`.

При первом запуске скрипт сам создаст виртуальное окружение `.venv/`,
установит зависимости из `requirements.txt` и откроет приложение в браузере
на [http://localhost:8501](http://localhost:8501). При повторных запусках — сразу
стартует Streamlit. Чтобы остановить — закройте окно консоли или нажмите Ctrl+C.

Требования: **Python 3.10+** в PATH (при установке в Windows отметьте
«Add Python to PATH»).

### Ручной запуск

```bash
git clone https://github.com/<your-account>/foundry-npc-builder.git
cd foundry-npc-builder

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

Откройте [http://localhost:8501](http://localhost:8501).

### Сборка в единый .exe

PyInstaller собирает бинарь только под ту ОС, на которой запущен, поэтому
`.exe` собирается на Windows-машине (или в GitHub Actions — см. ниже).
Результат весит ~200 MB и запускается без установленного Python.

#### Локально на Windows

Дважды щёлкните **`build.bat`**. Скрипт:

1. создаёт/переиспользует `.venv/`,
2. устанавливает `requirements.txt` + `pyinstaller`,
3. запускает `pyinstaller FoundryNPCBuilder.spec --clean --noconfirm`,
4. получаем `dist\FoundryNPCBuilder.exe`.

Сборка идёт 5–10 минут (в основном — первый `pip install`).

#### На macOS / Linux

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller FoundryNPCBuilder.spec --clean --noconfirm
```

Получится исполняемый файл под текущую ОС (без .exe).

#### Автоматически через GitHub Actions

В `.github/workflows/build-exe.yml` лежит готовый workflow. Два способа:

- **Manual run**: в репозитории идите Actions → *Build Windows EXE* → *Run workflow*.
  Через несколько минут скачайте `.exe` из вкладки *Artifacts*.
- **Через тэг**: любой пуш тэга `v*` (например `git tag v1.0 && git push --tags`)
  соберёт `.exe` и автоматически приложит его к Release.

Так вы получаете готовый `.exe` без Windows-машины под рукой.

## Как пользоваться

1. Заполните форму (имя обязательное, остальное — по необходимости).
2. По желанию загрузите портрет и токен (PNG/JPG/WEBP).
3. Нажмите **«Собрать JSON»** и кнопку скачивания.
4. В Foundry VTT откройте боковую панель **Actors** → **Import** и
   выберите скачанный файл.

## Маппинг полей формы → JSON Foundry

| Поле формы | Путь в JSON |
|------------|-------------|
| Имя | `name`, `prototypeToken.name` |
| Раса (название) | `system.details.type.subtype` |
| Раса (тип существа) | `system.details.type.value` (humanoid, fey, …) |
| Раса (размер) | `system.traits.size` |
| Раса (скорость) | `system.attributes.movement.walk` |
| Характеристики | `system.abilities.<str/dex/con/int/wis/cha>.value` |
| HP | `system.attributes.hp.value`, `hp.max` |
| Слоты заклинаний | `system.spells.spell1..spell9.value`, `pact` |
| Класс | помещается в краткое резюме биографии; `system.attributes.spellcasting` для заклинательных классов |
| Класс брони | `system.attributes.ac.calc = "custom"`, `formula` |
| Класс опасности | `system.details.cr` |
| Устойчивости | `system.traits.dr.value` |
| Невосприимчивости (урон) | `system.traits.di.value` |
| Уязвимости | `system.traits.dv.value` |
| Невосприимчивости (состояния) | `system.traits.ci.value` |
| Биография | `system.details.biography.value` (HTML) |
| Отношение к игрокам | `prototypeToken.disposition` (-1 / 0 / 1) |
| Портрет | `img`, как `data:image/...;base64,...` |
| Токен | `prototypeToken.texture.src` |

## Что НЕ настраивается в мастере

Намеренно не вынесены в форму — легче дозаполнить в листе персонажа Foundry
после импорта:

- владения навыками и спасбросками (`system.skills`, `abilities.*.proficient`),
- чувства — darkvision/blindsight/truesight (`system.attributes.senses`),
- языки (`system.traits.languages`),
- легендарные действия и логово (`system.resources.legact / legres / lair`),
- инвентарь и атаки (`items[]`),
- активные эффекты (`effects[]`),
- мировоззрение, идеалы, привязанности, недостатки.

Эти секции остаются в JSON как пустые структуры в соответствии со схемой
Foundry.

## Расширение справочников

Все списки рас, классов, типов урона и состояний — обычные JSON-файлы в
папке `data/`. Чтобы добавить, например, новую расу, достаточно дописать
запись в `data/races.json`:

```json
{"key": "shifter", "name": "Перевёртыш", "creature_type": "humanoid", "size": "med"}
```

Перезапуска кода не требуется — Streamlit перечитает файл при следующем
запросе (кэш `st.cache_data` сбрасывается при изменении файла на диске,
либо вручную через меню «Rerun»).

## Лицензия

[MIT](LICENSE).
