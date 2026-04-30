# Foundry VTT NPC Builder

Streamlit-приложение для быстрой сборки JSON-файла мастер-персонажа (NPC) для
[Foundry VTT](https://foundryvtt.com/) с системой **dnd5e**. Готовый файл
импортируется в Foundry через `Sidebar → Actors → Import`.

Тестировалось со связкой Foundry VTT core **13.x** и dnd5e **5.x** (правила 2014).

## Возможности

- **Имя, раса, класс, КО** — обязательные поля. КО берётся из таблицы DMG (CR 0…30 с XP).
- **Авторекомендации характеристик, КД, HP и слотов заклинаний** на основе сочетания
  «класс + КО»:
  - Профиль `[primary, secondary, tertiary, dump]` из `cr_scaling.json` распределяется
    по приоритету характеристик класса (волшебник → большой интеллект и низкая сила;
    варвар → сила и телосложение; жрец → мудрость; и т.д.).
  - HP = средний HP по КО × множитель класса (`hp_multiplier`).
  - КД = базовый КД по КО (`ac_base`) + модификатор класса (`ac_modifier`),
    но не ниже базового КД самого класса.
  - Слоты заклинаний: full / half / third / pact, рассчитываются от эквивалентного
    уровня заклинателя (`caster_level`) с учётом таблиц `spell_slots_by_level` и
    `pact_slots_by_level`.
- **Скорость от расы** — `system.attributes.movement.walk` берётся из `races.json`
  (дварф 25, кентавр 40, лесной эльф 35 и т.д.).
- **Ручное переопределение** любого рекомендованного значения прямо в интерфейсе.
- **Устойчивости / невосприимчивости / уязвимости** к типам урона.
- **Невосприимчивости к состояниям**.
- **Биография** — необязательное поле, попадает в `system.details.biography.value`.
- **Отношение к игрокам** — дружелюбный / нейтральный / враждебный (`prototypeToken.disposition`).
- **Загрузка портрета и токена** — изображения встраиваются в JSON как `data:` URI,
  файл самодостаточен.

## Структура репозитория

```
foundry-npc-builder/
├── app.py                       # Streamlit-приложение
├── data/
│   ├── races.json               # Расы: тип существа, размер, скорость
│   ├── classes.json             # Классы: base_ac, ac_modifier, hp_multiplier,
│   │                            #         ability_priority, caster_type
│   ├── damage_types.json        # Типы урона и состояния D&D 5e
│   ├── cr_table.json            # Таблица класса опасности (CR 0–30)
│   └── cr_scaling.json          # Скейлинг HP/AC/хар-к/слотов по CR
├── templates/
│   └── npc_template.json        # Базовая структура NPC Actor
├── .streamlit/config.toml       # Настройки темы и upload-лимита
├── requirements.txt
├── LICENSE
└── README.md
```

## Установка и запуск

```bash
git clone https://github.com/<your-account>/foundry-npc-builder.git
cd foundry-npc-builder

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

Откройте [http://localhost:8501](http://localhost:8501).

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
