"""
Foundry VTT NPC Builder
=======================
Streamlit-приложение для создания JSON-файла NPC (мастер-персонажа) для Foundry VTT
с системой dnd5e. Сгенерированный файл можно импортировать в Foundry через
Sidebar → Actors → Import.

Логика автозаполнения:
  - Раса задаёт тип существа, размер и скорость (data/races.json).
  - Класс задаёт базовый КД, профиль приоритета характеристик, тип
    заклинательства и множитель HP (data/classes.json).
  - Класс опасности задаёт усреднённое HP, базовый КД, профиль значений
    характеристик [primary, secondary, tertiary, dump] и эквивалентный
    уровень заклинателя (data/cr_scaling.json).

Запуск: streamlit run app.py
"""

from __future__ import annotations

import base64
import copy
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Конфигурация и загрузка справочников
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
TEMPLATE_PATH = ROOT / "templates" / "npc_template.json"


@st.cache_data(show_spinner=False)
def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


RACES = load_json(DATA_DIR / "races.json")["races"]
CLASSES = load_json(DATA_DIR / "classes.json")["classes"]
DAMAGE_TYPES = load_json(DATA_DIR / "damage_types.json")["damage_types"]
CONDITIONS = load_json(DATA_DIR / "damage_types.json")["conditions"]
CR_TABLE = load_json(DATA_DIR / "cr_table.json")["values"]
CR_SCALING = load_json(DATA_DIR / "cr_scaling.json")
LEVEL_SCALING = load_json(DATA_DIR / "level_scaling.json")
CREATURE_TYPES = load_json(DATA_DIR / "creature_types.json")["creature_types"]
SIZES = load_json(DATA_DIR / "sizes.json")["sizes"]


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

DISPOSITION_MAP = {
    "Дружелюбный": 1,
    "Нейтральный": 0,
    "Враждебный": -1,
}

ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"]
ABILITY_LABELS = {
    "str": "Сила",
    "dex": "Ловкость",
    "con": "Телосложение",
    "int": "Интеллект",
    "wis": "Мудрость",
    "cha": "Харизма",
}


def random_id(length: int = 16) -> str:
    raw = uuid.uuid4().hex + uuid.uuid4().hex
    return raw[:length]


def slugify(text: str) -> str:
    text = (text or "npc").strip().lower()
    text = re.sub(r"[^\w\-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "npc"


def file_to_data_uri(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None
    # Сбрасываем позицию на случай, если файл уже читался для превью через st.image
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    data = uploaded_file.read()
    mime = uploaded_file.type or "image/png"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def level_to_cr_label(level: int) -> str:
    """Приближённый эквивалент КО для NPC-персонажа в Foundry.
    Используется только для записи в system.details.cr (лента фактов-XP в Foundry)."""
    mapping = {
        1: "1/4", 2: "1/2", 3: "1",  4: "1",  5: "2",
        6: "3",   7: "3",   8: "4",  9: "5",  10: "6",
        11: "7",  12: "8",  13: "9", 14: "10", 15: "12",
        16: "13", 17: "14", 18: "16", 19: "18", 20: "20",
    }
    return mapping.get(level, "1")


def cr_label_to_key(label: str) -> str:
    """'1/4' → '0.25', '6' → '6'."""
    mapping = {"0": "0", "1/8": "0.125", "1/4": "0.25", "1/2": "0.5"}
    if label in mapping:
        return mapping[label]
    # Целочисленные КО
    return str(int(float(label))) if "/" not in label else mapping.get(label, label)


# ---------------------------------------------------------------------------
# Рекомендательные расчёты (модальные по режиму «CR» / «LEVEL»)
# ---------------------------------------------------------------------------

MODE_CR = "cr"
MODE_LEVEL = "level"


def scaling_row(mode: str, key: str) -> dict:
    """Единая точка доступа к строке скалирования для режима CR/Level.
    Для CR ключ — строковое представление типа '0.25' / '1' / '12'.
    Для Level ключ — строковой уровень '1'...'20'."""
    if mode == MODE_CR:
        return CR_SCALING["scaling"][key]
    return LEVEL_SCALING["scaling"][key]


def recommend_abilities(cls: dict, mode: str, key: str) -> dict[str, int]:
    """Распределяет [primary, secondary, tertiary, dump] по приоритетам класса."""
    profile = scaling_row(mode, key)["ability_profile"]
    primary, secondary, tertiary, dump = profile
    priority = cls["ability_priority"]
    result: dict[str, int] = {}
    for idx, ability in enumerate(priority):
        if idx == 0:
            result[ability] = primary
        elif idx == 1:
            result[ability] = secondary
        elif idx == 2:
            result[ability] = tertiary
        else:
            result[ability] = dump
    return result


def recommend_hp(cls: dict, mode: str, key: str) -> int:
    base = scaling_row(mode, key)["hp_avg"]
    return max(1, round(base * cls["hp_multiplier"]))


def recommend_ac(cls: dict, mode: str, key: str) -> int:
    """ac_base корректируется ac_modifier класса, не ниже class.base_ac."""
    base = scaling_row(mode, key)["ac_base"]
    return max(cls["base_ac"], base + cls["ac_modifier"])


def recommend_spell_slots(cls: dict, mode: str, key: str) -> tuple[dict[str, int], dict | None]:
    """Возвращает (slots_dict, pact_dict).
    slots_dict — {'spell1': N, ...} для full/half/third caster.
    pact_dict — {'value': N, 'level': L} для pact-кастера или None."""
    caster_type = cls["caster_type"]
    if caster_type == "none":
        return {}, None

    full_level = scaling_row(mode, key)["caster_level"]

    if caster_type == "full":
        level = full_level
    elif caster_type == "half":
        level = max(1, round(full_level / 2))
    elif caster_type == "third":
        level = max(1, round(full_level / 3))
    elif caster_type == "pact":
        level = max(1, min(20, full_level))
        pact = CR_SCALING["pact_slots_by_level"][str(level)]
        return {}, pact
    else:
        return {}, None

    level = max(1, min(20, level))
    slots_list = CR_SCALING["spell_slots_by_level"][str(level)]
    slots = {f"spell{i+1}": v for i, v in enumerate(slots_list)}
    return slots, None


# ---------------------------------------------------------------------------
# Сборка JSON
# ---------------------------------------------------------------------------

def build_npc_json(form: dict[str, Any]) -> dict:
    template = load_json(TEMPLATE_PATH)
    npc = copy.deepcopy(template)

    now_ms = int(time.time() * 1000)
    npc["_id"] = random_id()
    npc["_stats"]["createdTime"] = now_ms
    npc["_stats"]["modifiedTime"] = now_ms

    name = form["name"].strip() or "Безымянный NPC"
    npc["name"] = name
    npc["prototypeToken"]["name"] = name

    # Тип существа и подтип (раса / свободный текст)
    creature_type = form["creature_type"]
    race = form.get("race")
    npc["system"]["details"]["type"]["value"] = creature_type["key"]
    if race:
        npc["system"]["details"]["type"]["subtype"] = race["name"]
    else:
        npc["system"]["details"]["type"]["subtype"] = (form.get("subtype_text") or "").strip()

    # Размер + размер токена
    size = form["size"]
    npc["system"]["traits"]["size"] = size["key"]
    npc["prototypeToken"]["width"] = size["width"]
    npc["prototypeToken"]["height"] = size["height"]

    # Скорость
    npc["system"]["attributes"]["movement"]["walk"] = int(form["speed"])

    # Класс — отметка spellcasting-характеристики
    cls = form["class"]
    if cls["caster_type"] != "none":
        # primary ability у заклинателей фактически совпадает с заклинательной
        npc["system"]["attributes"]["spellcasting"] = cls["ability_priority"][0]

    # КД
    ac_value = int(form["ac"])
    npc["system"]["attributes"]["ac"]["calc"] = "custom"
    npc["system"]["attributes"]["ac"]["formula"] = str(ac_value)

    # HP
    hp_value = int(form["hp"])
    npc["system"]["attributes"]["hp"]["value"] = hp_value
    npc["system"]["attributes"]["hp"]["max"] = hp_value

    # Класс опасности
    npc["system"]["details"]["cr"] = form["cr_value"]

    # Характеристики
    for ab, val in form["abilities"].items():
        npc["system"]["abilities"][ab]["value"] = int(val)

    # Слоты заклинаний
    for key, value in form["spell_slots"].items():
        npc["system"]["spells"][key]["value"] = int(value)
        npc["system"]["spells"][key]["override"] = int(value)
    if form.get("pact_slots"):
        npc["system"]["spells"]["pact"] = {
            "value": int(form["pact_slots"]["value"]),
            "max": int(form["pact_slots"]["value"]),
            "level": int(form["pact_slots"]["level"]),
            "override": int(form["pact_slots"]["value"]),
        }

    # Устойчивости / уязвимости / невосприимчивости
    npc["system"]["traits"]["dr"]["value"] = form["dr"]
    npc["system"]["traits"]["di"]["value"] = form["di"]
    npc["system"]["traits"]["dv"]["value"] = form["dv"]
    npc["system"]["traits"]["ci"]["value"] = form["ci"]

    # Биография
    if race:
        descriptor = race["name"]
    elif (form.get("subtype_text") or "").strip():
        descriptor = f"{creature_type['name']} ({form['subtype_text'].strip()})"
    else:
        descriptor = creature_type["name"]
    rank_text = (
        f"КО {form['cr_label']}" if form.get("mode") == MODE_CR
        else f"ур. {form.get('level')}"
    )
    summary = (
        f"<p><strong>{name}</strong> — {descriptor}, {cls['name']} "
        f"(КД {ac_value}, ХП {hp_value}, {rank_text}).</p>"
    )
    bio = form["biography"].strip()
    bio_html = ""
    if bio:
        bio_html = "<p>" + bio.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    npc["system"]["details"]["biography"]["value"] = summary + bio_html

    # Disposition
    npc["prototypeToken"]["disposition"] = DISPOSITION_MAP[form["disposition"]]

    # Картинки
    portrait_uri = form.get("portrait_uri")
    if portrait_uri:
        npc["img"] = portrait_uri
    token_uri = form.get("token_uri") or portrait_uri
    if token_uri:
        npc["prototypeToken"]["texture"]["src"] = token_uri

    return npc


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Foundry VTT NPC Builder",
    page_icon="🎲",
    layout="wide",
)

st.title("🎲 Foundry VTT NPC Builder")
st.caption(
    "Сборка JSON-файла мастер-персонажа (NPC) для Foundry VTT, система dnd5e. "
    "Класс и класс опасности автоматически дают рекомендуемые характеристики, "
    "КД, хиты и слоты заклинаний — их можно при желании поправить вручную."
)

# --- 1. Базовые поля (вне формы — нужны для пересчёта рекомендаций при изменении) ---

st.subheader("Основное")

# Имя и чекбокс «Монстр»
col_name, col_monster = st.columns([3, 1])
with col_name:
    name = st.text_input("Имя персонажа *", value="", max_chars=120, key="name")
with col_monster:
    is_monster = st.checkbox(
        "Монстр",
        value=False,
        key="is_monster",
        help=(
            "Если отмечено — выбираете тип существа (нежить, исчадие и т.д.). "
            "Если выбран «Гуманоид» — остаётся обычный выбор расы. "
            "Для других типов появится поле «Подтип» (свободный текст)."
        ),
    )

# Тип существа / раса / подтип / размер
DEFAULT_SIZE_KEY = "med"
DEFAULT_SIZE_IDX = next(
    (i for i, s in enumerate(SIZES) if s["key"] == DEFAULT_SIZE_KEY), 2
)

if is_monster:
    col_type, col_subtype, col_size = st.columns(3)
    with col_type:
        ctype_idx = st.selectbox(
            "Тип существа",
            options=list(range(len(CREATURE_TYPES))),
            format_func=lambda i: CREATURE_TYPES[i]["name"],
            key="ctype_idx",
        )
        creature_type = CREATURE_TYPES[ctype_idx]
    is_humanoid = creature_type["key"] == "humanoid"

    with col_subtype:
        if is_humanoid:
            race_idx = st.selectbox(
                "Раса", options=list(range(len(RACES))),
                format_func=lambda i: f"{RACES[i]['name']} ({RACES[i]['speed']} фт)",
                key="race_idx_monster",
            )
            race = RACES[race_idx]
            subtype_text = ""
        else:
            race = None
            subtype_text = st.text_input(
                "Подтип",
                value="",
                max_chars=120,
                key="subtype_text",
                help="Свободное описание подтипа (например, «лич», «демон-балор»).",
            )
    with col_size:
        size_idx = st.selectbox(
            "Размер существа",
            options=list(range(len(SIZES))),
            format_func=lambda i: SIZES[i]["name"],
            index=DEFAULT_SIZE_IDX,
            key="size_idx",
        )
else:
    # Обычный режим: NPC = персонаж, выбираем расу, тип = «Гуманоид»
    creature_type = next(
        (ct for ct in CREATURE_TYPES if ct["key"] == "humanoid"),
        CREATURE_TYPES[0],
    )
    subtype_text = ""
    col_race, col_size = st.columns(2)
    with col_race:
        race_idx = st.selectbox(
            "Раса", options=list(range(len(RACES))),
            format_func=lambda i: f"{RACES[i]['name']} ({RACES[i]['speed']} фт)",
            key="race_idx",
        )
        race = RACES[race_idx]
    with col_size:
        # По умолчанию подставляем размер расы, если он задан
        race_size_idx = next(
            (i for i, s in enumerate(SIZES) if s["key"] == race.get("size")),
            DEFAULT_SIZE_IDX,
        )
        size_idx = st.selectbox(
            "Размер существа",
            options=list(range(len(SIZES))),
            format_func=lambda i: SIZES[i]["name"],
            index=race_size_idx,
            key=f"size_idx_race_{race['key']}",
        )

size = SIZES[size_idx]

# Класс / КО или уровень / отношение
col_cls, col_rank, col_disp = st.columns([1, 1, 1.4])
with col_cls:
    class_idx = st.selectbox(
        "Класс", options=list(range(len(CLASSES))),
        format_func=lambda i: CLASSES[i]["name"],
        key="class_idx",
    )
    cls = CLASSES[class_idx]
with col_rank:
    if is_monster:
        cr_idx = st.selectbox(
            "Класс опасности (КО)",
            options=list(range(len(CR_TABLE))),
            format_func=lambda i: f"{CR_TABLE[i]['label']}  ({CR_TABLE[i]['xp']} XP)",
            index=4,  # CR 1
            key="cr_idx",
        )
        cr_label = CR_TABLE[cr_idx]["label"]
        cr_value = CR_TABLE[cr_idx]["value"]
        level = None
        mode = MODE_CR
        scaling_key = cr_label_to_key(cr_label)
    else:
        level = st.number_input(
            "Уровень персонажа",
            min_value=1, max_value=20, value=1, step=1, key="level",
            help="На уровне основаны HP, КД, характеристики и слоты заклинаний (PHB).",
        )
        mode = MODE_LEVEL
        scaling_key = str(int(level))
        cr_label = level_to_cr_label(int(level))
        # Подбираем cr_value из CR_TABLE по аппроксимации
        cr_value = next((row["value"] for row in CR_TABLE if row["label"] == cr_label), 1)
with col_disp:
    disposition = st.radio(
        "Отношение к игрокам",
        options=list(DISPOSITION_MAP.keys()),
        index=1,
        horizontal=True,
        key="disposition",
    )

# --- 2. Автоматические рекомендации ---
rec_abilities = recommend_abilities(cls, mode, scaling_key)
rec_hp = recommend_hp(cls, mode, scaling_key)
rec_ac = recommend_ac(cls, mode, scaling_key)
rec_slots, rec_pact = recommend_spell_slots(cls, mode, scaling_key)

# Динамический суффикс: при смене класса/CR/уровня/расы виджеты
# пересоздаются и подставляют свежие рекомендации.
race_ctx_key = race["key"] if race else f"{creature_type['key']}-{(subtype_text or '').strip().lower() or 'none'}"
rank_token = f"cr{cr_label}" if mode == MODE_CR else f"lvl{level}"
ctx = f"{cls['key']}__{rank_token}__{race_ctx_key}"

st.divider()
st.subheader("Боевые параметры (рекомендации можно править)")

col_ac, col_hp, col_speed = st.columns(3)
with col_ac:
    ac = st.number_input(
        "Класс брони (КД)", min_value=1, max_value=40, value=rec_ac,
        help=(
            f"Рекомендация для «{cls['name']}» при {'КО ' + cr_label if mode == MODE_CR else 'ур. ' + str(level)}: {rec_ac}. "
            f"Рассчитан как ac_base({scaling_row(mode, scaling_key)['ac_base']}) "
            f"+ модификатор класса({cls['ac_modifier']:+d}), "
            f"но не ниже базы класса ({cls['base_ac']})."
        ),
        key=f"ac_{ctx}",
    )
with col_hp:
    hp_help_base = scaling_row(mode, scaling_key)["hp_avg"]
    if mode == MODE_CR:
        hp_help = (
            f"Усреднённое HP монстров КО {cr_label} по бестиарию: {hp_help_base}, "
            f"с множителем класса ({cls['hp_multiplier']}) = {rec_hp}."
        )
    else:
        hp_help = (
            f"Стандартный PC-расчёт по PHB: ур. {level}, база d8+CON "
            f"= {hp_help_base}, × множитель класса ({cls['hit_die']}, {cls['hp_multiplier']}) = {rec_hp}."
        )
    hp = st.number_input(
        "Хиты (HP)", min_value=1, max_value=2000, value=rec_hp,
        help=hp_help,
        key=f"hp_{ctx}",
    )
with col_speed:
    default_speed = int(race["speed"]) if race else 30
    speed_help = (
        f"Базовая скорость расы «{race['name']}»: {race['speed']} фт."
        if race else
        "Раса не выбрана (монстр не-гуманоид). Значение по умолчанию — 30 фт."
    )
    speed = st.number_input(
        "Скорость (фт)", min_value=0, max_value=120, value=default_speed,
        help=speed_help,
        key=f"speed_{ctx}",
    )

st.markdown("**Характеристики** (распределены по приоритету класса)")
ab_cols = st.columns(6)
abilities: dict[str, int] = {}
for col, ab in zip(ab_cols, ABILITY_KEYS):
    with col:
        abilities[ab] = st.number_input(
            ABILITY_LABELS[ab], min_value=1, max_value=30,
            value=rec_abilities[ab],
            key=f"ab_{ab}_{ctx}",
        )

# --- 3. Заклинания ---
if cls["caster_type"] != "none":
    with st.expander(f"Слоты заклинаний (caster: {cls['caster_type']})", expanded=False):
        if rec_pact:
            st.markdown(
                f"**Pact magic:** {rec_pact['value']} слот(а) уровня {rec_pact['level']} "
                "(колдун)."
            )
            pact_value = st.number_input(
                "Слотов pact", min_value=0, max_value=10,
                value=int(rec_pact["value"]), key=f"pact_value_{ctx}",
            )
            pact_level = st.number_input(
                "Уровень pact-слотов", min_value=1, max_value=9,
                value=int(rec_pact["level"]), key=f"pact_level_{ctx}",
            )
            slot_overrides: dict[str, int] = {}
            pact_slots = {"value": pact_value, "level": pact_level}
        else:
            slot_overrides = {}
            slot_cols = st.columns(9)
            for i, c in enumerate(slot_cols, start=1):
                slot_key = f"spell{i}"
                with c:
                    slot_overrides[slot_key] = st.number_input(
                        f"{i} ур.", min_value=0, max_value=20,
                        value=int(rec_slots.get(slot_key, 0)),
                        key=f"slot_{i}_{ctx}",
                    )
            pact_slots = None
else:
    slot_overrides = {}
    pact_slots = None

# --- 4. Устойчивости и невосприимчивости ---
with st.expander("Устойчивости и невосприимчивости", expanded=False):
    damage_options = {dt["key"]: dt["name"] for dt in DAMAGE_TYPES}
    condition_options = {c["key"]: c["name"] for c in CONDITIONS}

    dr_keys = st.multiselect("Устойчивости к урону", options=list(damage_options.keys()),
                             format_func=lambda k: damage_options[k], key="dr")
    di_keys = st.multiselect("Невосприимчивости к урону", options=list(damage_options.keys()),
                             format_func=lambda k: damage_options[k], key="di")
    dv_keys = st.multiselect("Уязвимости к урону", options=list(damage_options.keys()),
                             format_func=lambda k: damage_options[k], key="dv")
    ci_keys = st.multiselect("Невосприимчивости к состояниям",
                             options=list(condition_options.keys()),
                             format_func=lambda k: condition_options[k], key="ci",
                             help="Устойчивости к состояниям правилами 5e не предусмотрены.")

# --- 5. Биография и изображения ---
st.subheader("Биография и изображения")
biography = st.text_area("Биография (необязательно)", value="", height=160, key="bio")

PREVIEW_PX = 180  # размер миниатюры превью (≈4 от общей ширины)

col_p, col_t = st.columns(2)
with col_p:
    portrait_file = st.file_uploader(
        "Портрет (img)", type=["png", "jpg", "jpeg", "webp", "gif"], key="portrait",
    )
    if portrait_file is not None:
        try:
            portrait_file.seek(0)
        except Exception:
            pass
        st.image(portrait_file, width=PREVIEW_PX, caption="Предпросмотр портрета")
with col_t:
    token_file = st.file_uploader(
        "Токен", type=["png", "jpg", "jpeg", "webp"], key="token",
        help="Если не загружен — будет использован портрет.",
    )
    if token_file is not None:
        try:
            token_file.seek(0)
        except Exception:
            pass
        st.image(token_file, width=PREVIEW_PX, caption="Предпросмотр токена")
    elif portrait_file is not None:
        st.caption("Токен не загружен — в Foundry попадёт портрет.")

# --- 6. Кнопка ---
st.divider()
if st.button("✨ Собрать JSON", type="primary", use_container_width=True):
    if not name.strip():
        st.error("Имя персонажа обязательно.")
        st.stop()

    portrait_uri = file_to_data_uri(portrait_file) if portrait_file else None
    token_uri = file_to_data_uri(token_file) if token_file else None

    # Подменяем расовую скорость пользовательским значением (если раса выбрана)
    race_for_build = dict(race) if race else None
    if race_for_build is not None:
        race_for_build["speed"] = speed

    form = {
        "name": name,
        "creature_type": creature_type,
        "race": race_for_build,
        "subtype_text": subtype_text,
        "size": size,
        "speed": speed,
        "class": cls,
        "ac": ac,
        "hp": hp,
        "abilities": abilities,
        "spell_slots": slot_overrides,
        "pact_slots": pact_slots,
        "cr_label": cr_label,
        "cr_value": cr_value,
        "mode": mode,
        "level": int(level) if level is not None else None,
        "disposition": disposition,
        "dr": dr_keys, "di": di_keys, "dv": dv_keys, "ci": ci_keys,
        "biography": biography,
        "portrait_uri": portrait_uri,
        "token_uri": token_uri,
    }
    npc_json = build_npc_json(form)

    st.success(f"NPC «{name}» успешно собран.")
    pretty = json.dumps(npc_json, ensure_ascii=False, indent=2)
    file_name = f"fvtt-Actor-{slugify(name)}-{npc_json['_id']}.json"

    st.download_button(
        label="⬇️ Скачать JSON для Foundry VTT",
        data=pretty.encode("utf-8"),
        file_name=file_name,
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("Превью JSON"):
        st.code(pretty, language="json")

# --- Sidebar ---
with st.sidebar:
    st.header("Текущие рекомендации")
    if race:
        type_line = f"**Раса:** {race['name']}"
        speed_line = f"**Скорость (база):** {race['speed']} фт"
    else:
        sub = (subtype_text or "—").strip() or "—"
        type_line = f"**Тип:** {creature_type['name']}  \n**Подтип:** {sub}"
        speed_line = "**Скорость:** задаётся вручную"
    if mode == MODE_CR:
        rank_line = f"**КО:** {cr_label}"
    else:
        rank_line = f"**Уровень:** {level} _(≈КО {cr_label} для Foundry)_"
    st.markdown(
        f"**Класс:** {cls['name']}  \n"
        f"{type_line}  \n"
        f"**Размер:** {size['name']} ({size['width']}×{size['height']})  \n"
        f"{rank_line}  \n\n"
        f"**Рекомендация HP:** {rec_hp}  \n"
        f"**Рекомендация КД:** {rec_ac}  \n"
        f"{speed_line}"
    )
    st.divider()
    st.markdown("**Профиль характеристик**")
    for ab in ABILITY_KEYS:
        st.markdown(f"- {ABILITY_LABELS[ab]}: **{rec_abilities[ab]}**")
    if rec_slots:
        st.divider()
        st.markdown("**Слоты заклинаний**")
        for i in range(1, 10):
            v = rec_slots.get(f"spell{i}", 0)
            if v:
                st.markdown(f"- {i} ур.: {v}")
    if rec_pact:
        st.divider()
        st.markdown(
            f"**Pact magic:** {rec_pact['value']} × ур. {rec_pact['level']}"
        )
    st.divider()
    st.caption(
        "Все справочники (расы, классы, шкала CR, типы урона) лежат в папке "
        "`data/` и редактируются как обычные JSON-файлы."
    )
