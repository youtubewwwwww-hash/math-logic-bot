import heapq
import itertools
import math
import re
from collections import defaultdict
import asyncio
import io

try:
    import networkx as nx
except ImportError:
    nx = None

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Yangi google-genai kutubxonasi va Interactions API
from google import genai
from PIL import Image
import base64

# --- SOZLAMALAR ---
TOKEN = "9009553554:AAH6zD3cYhQ6K-kNHyIchRGYmdvek9LRg3M"
ADMIN_ID = 6484242904

# Siz taqdim etgan yangi AQ tokeni
GEMINI_API_KEY = "AQ.Ab8RN6JA5cyok39CKYcmcXDZezm5B20xkBElkasL7c2fpwKhAg"

# Interactions API uchun client (v1beta yoki standart)
client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1beta"})

bot = Bot(token=TOKEN)
dp = Dispatcher()

waiting_for_feedback = set()

# ---------------------------------------------------------------- MATEMATIKA VA DISKRET TUZILMALAR
def _sort_key(x):
    try:
        return (0, float(x), x)
    except ValueError:
        return (1, 0.0, x)

def fmt_set(s):
    return "{" + ", ".join(sorted(s, key=_sort_key)) + "}" if s else "∅"

def parse_set(text):
    return {x for x in re.split(r"[,\s;]+", text.strip().strip("{}").strip()) if x}

def fmt_num(x):
    x = float(x)
    return str(int(x)) if x.is_integer() else str(x)

def sets_solver(args):
    parts = args.split("|")
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError("Format: A | B | U\n(Masalan: 1,2,3 | 2,3,4 | 1,2,3,4,5)")
    A, B = parse_set(parts[0]), parse_set(parts[1])
    U = None
    if len(parts) >= 3 and parts[2].strip():
        U = parse_set(parts[2])
        if not (A <= U and B <= U):
            raise ValueError("A va B to'plamlari universal U ning qismi bo'lishi kerak.")
    inter, union = A & B, A | B
    out = [f"A = {fmt_set(A)}", f"B = {fmt_set(B)}"]
    if U is not None:
        out.append(f"U = {fmt_set(U)}")
    out += [
        "",
        f"A ∪ B = {fmt_set(union)}",
        f"A ∩ B = {fmt_set(inter)}",
        f"A \\ B = {fmt_set(A - B)}",
        f"B \\ A = {fmt_set(B - A)}",
        f"A Δ B = {fmt_set(A ^ B)}   (simmetrik ayirma)",
        "",
        f"|A| = {len(A)},  |B| = {len(B)}",
        f"|A ∪ B| = |A| + |B| − |A ∩ B| = {len(A)} + {len(B)} − {len(inter)} = {len(union)}",
        f"A to'plamosti soni: 2^{len(A)} = {2 ** len(A)}",
        f"B to'plamosti soni: 2^{len(B)} = {2 ** len(B)}",
        f"|A × B| = {len(A)}·{len(B)} = {len(A) * len(B)}",
        f"A ⊆ B: {'ha' if A <= B else 'yo‘q'};  B ⊆ A: {'ha' if B <= A else 'yo‘q'}",
    ]
    return "\n".join(out)

def comb_solver(args):
    nums = re.findall(r"\d+", args)
    if len(nums) not in (1, 2):
        raise ValueError("Format: n k   (masalan: 5 2)")
    n = int(nums[0])
    k = int(nums[1]) if len(nums) == 2 else None
    if n > 300 or (k is not None and k > 300):
        raise ValueError("Sonlar 300 dan oshmasin.")
    out = [f"{n}! = {math.factorial(n)}"]
    if k is not None:
        if k <= n:
            out.append(f"O'rinlashtirish  A({n},{k}) = {math.perm(n, k)}")
            out.append(f"Guruhlash        C({n},{k}) = {math.comb(n, k)}")
        else:
            out.append(f"k > n bo'lgani uchun takrorsiz A({n},{k}) = 0 va C({n},{k}) = 0")
        out.append(f"Takroriy o'rinlashtirish  {n}^{k} = {n ** k}")
    return "\n".join(out)

def rel_solver(args):
    parts = args.split("|")
    if len(parts) < 2:
        raise ValueError("Format: X | R\n(Masalan: 1,2,3 | 1-1 2-2 3-3 1-2)")
    X = parse_set(parts[0])
    R = set(re.findall(r"(\w+)\s*-\s*(\w+)", parts[1]))
    if not X or not R:
        raise ValueError("To'plam va juftliklarni to'g'ri yozing.")
    bad = [p for p in R if p[0] not in X or p[1] not in X]
    if bad:
        raise ValueError(f"Juftlik to'plamdan tashqarida: {bad[0][0]}-{bad[0][1]}")
    xs = sorted(X, key=_sort_key)
    P = lambda p: f"({p[0]},{p[1]})"
    out = [f"X = {fmt_set(X)}", "R = {" + ", ".join(P(p) for p in sorted(R, key=lambda p: (_sort_key(p[0]), _sort_key(p[1])))) + "}"]
    
    miss = [x for x in xs if (x, x) not in R]
    refl = not miss
    sym_v = next(((a, b) for a, b in R if (b, a) not in R), None)
    anti_v = next(((a, b) for a, b in R if a != b and (b, a) in R), None)
    trans_v = next(((a, b, d) for a, b in R for c, d in R if b == c and (a, d) not in R), None)
    sym, anti, trans = sym_v is None, anti_v is None, trans_v is None

    ok = lambda v: "ha ✅" if v else "yo‘q ❌"
    out += ["", "Xossalar:"]
    out.append(f"  Refleksiv: {ok(refl)}")
    out.append(f"  Simmetrik: {ok(sym)}")
    out.append(f"  Antisimmetrik: {ok(anti)}")
    out.append(f"  Tranzitiv: {ok(trans)}")
    return "\n".join(out)

_TOK = re.compile(r"\s*(<->|<=>|->|=>|↔|→|∧|¬|⊕|&|\||\^|!|~|\(|\)|[A-Za-z_]\w*|[01])")
_KIND = {
    "not": "NOT", "¬": "NOT", "!": "NOT", "~": "NOT",
    "and": "AND", "∧": "AND", "&": "AND",
    "or": "OR", "∨": "OR", "|": "OR",
    "xor": "XOR", "⊕": "XOR", "^": "XOR",
    "->": "IMP", "=>": "IMP", "→": "IMP",
    "<->": "EQV", "<=>": "EQV", "↔": "EQV",
    "(": "LP", ")": "RP",
    "0": "C0", "1": "C1", "false": "C0", "true": "C1",
}

def _tokenize(expr):
    pos, toks = 0, []
    expr = expr.rstrip()
    while pos < len(expr):
        m = _TOK.match(expr, pos)
        if not m:
            raise ValueError(f"Tushunarsiz belgi: {expr[pos:].strip()[:10]}")
        raw = m.group(1)
        toks.append((_KIND.get(raw.lower(), "NAME"), raw))
        pos = m.end()
    return toks

class _Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0
    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None
    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok
    def parse(self):
        node = self.eqv()
        if self.i != len(self.t):
            raise ValueError("Ifoda noto'g'ri tugagan.")
        return node
    def eqv(self):
        left = self.imp()
        while self.peek() == "EQV":
            self.take()
            left = ("eqv", left, self.imp())
        return left
    def imp(self):
        left = self.xor()
        if self.peek() == "IMP":
            self.take()
            return ("imp", left, self.imp())
        return left
    def xor(self):
        left = self.or_()
        while self.peek() == "XOR":
            self.take()
            left = ("xor", left, self.or_())
        return left
    def or_(self):
        left = self.and_()
        while self.peek() == "OR":
            self.take()
            left = ("or", left, self.and_())
        return left
    def and_(self):
        left = self.not_()
        while self.peek() == "AND":
            self.take()
            left = ("and", left, self.not_())
        return left
    def not_(self):
        if self.peek() == "NOT":
            self.take()
            return ("not", self.not_())
        return self.atom()
    def atom(self):
        k = self.peek()
        if k is None:
            raise ValueError("Ifoda to'liq emas.")
        if k == "LP":
            self.take()
            node = self.eqv()
            if self.peek() != "RP":
                raise ValueError("Qavs yopilmagan.")
            self.take()
            return node
        if k == "NAME":
            return ("var", self.take()[1])
        if k in ("C0", "C1"):
            self.take()
            return ("const", k == "C1")
        raise ValueError("Ifoda noto'g'ri tuzilgan.")

def _vars(n):
    if n[0] == "var":
        return {n[1]}
    if n[0] == "const":
        return set()
    return set().union(*[_vars(c) for c in n[1:]])

def _ev(n, env):
    op = n[0]
    if op == "var":
        return env[n[1]]
    if op == "const":
        return n[1]
    if op == "not":
        return not _ev(n[1], env)
    a, b = _ev(n[1], env), _ev(n[2], env)
    return {"and": a and b, "or": a or b, "xor": a != b, "imp": (not a) or b, "eqv": a == b}[op]

def truth_table(expr):
    tree = _Parser(_tokenize(expr)).parse()
    names = sorted(_vars(tree))
    if not names:
        raise ValueError("O'zgaruvchi yo'q.")
    if len(names) > 6:
        raise ValueError("Ko'pi bilan 6 ta o'zgaruvchi.")
    lines = [" ".join(names) + " | F"]
    ones, zeros = [], []
    for vals in itertools.product([True, False], repeat=len(names)):
        env = dict(zip(names, vals))
        res = _ev(tree, env)
        row = " ".join(str(int(v)).ljust(len(nm)) for v, nm in zip(vals, names))
        lines.append(f"{row} | {int(res)}")
        (ones if res else zeros).append(vals)

    if not zeros:
        kind = "TAVTOLOGIYA (doim rost)"
    elif not ones:
        kind = "ZIDDIYAT (doim yolg'on)"
    else:
        kind = "bajariluvchi"
    lines += ["", f"Turi: {kind}"]
    return "\n".join(lines)

_EDGE = re.compile(r"([A-Za-z0-9_]+)\s*-\s*([A-Za-z0-9_]+)(?:\s*:\s*(-?\d+(?:\.\d+)?))?")

def parse_graph(text):
    t = text.strip()
    directed = False
    if re.match(r"dir\b", t, re.I):
        directed, t = True, t[3:]
    edges = [(u, v, float(w) if w else 1.0) for u, v, w in _EDGE.findall(t)]
    if not edges:
        raise ValueError("Qirralarni yozing: 1-2 2-3")
    V = sorted({x for u, v, _ in edges for x in (u, v)}, key=_sort_key)
    E, seen = [], set()
    for u, v, w in edges:
        key = (u, v) if directed else frozenset((u, v))
        if key not in seen:
            seen.add(key)
            E.append((u, v, w))
    return directed, V, E

def graph_solver(args):
    directed, V, E = parse_graph(args)
    n, m = len(V), len(E)
    out = [f"{'Yo‘naltirilgan' if directed else 'Yo‘naltirilmagan'} graf: {n} ta uchi, {m} ta qirra"]
    out.append("Uchlar: " + ", ".join(V))
    return "\n".join(out)

def path_solver(args):
    parts = args.split("|", 1)
    if len(parts) != 2:
        raise ValueError("Format: u v | qirralar (Masalan: 1 4 | 1-2:5 2-3:1)")
    ends = re.findall(r"[A-Za-z0-9_]+", parts[0])
    s, t = ends[0], ends[1]
    directed, V, E = parse_graph(parts[1])
    adj = defaultdict(list)
    for u, v, w in E:
        adj[u].append((v, w))
        if not directed:
            adj[v].append((u, w))
    dist, prev = {s: 0.0}, {}
    heap = [(0.0, _sort_key(s), s)]
    done = set()
    while heap:
        d, _, x = heapq.heappop(heap)
        if x in done:
            continue
        done.add(x)
        for y, w in adj[x]:
            nd = d + w
            if y not in dist or nd < dist[y]:
                dist[y], prev[y] = nd, x
                heapq.heappush(heap, (nd, _sort_key(y), y))
    out = [f"Dijkstra, boshlanish: {s}", ""]
    if t not in dist:
        out.append(f"{s} dan {t} ga yo‘l yo‘q.")
    else:
        path, x = [t], t
        while x != s:
            x = prev[x]
            path.append(x)
        out.append(f"Eng qisqa yo‘l: " + " → ".join(reversed(path)))
        out.append(f"Uzunligi: {fmt_num(dist[t])}")
    return "\n".join(out)

# ---------------------------------------------------------------- TELEGRAM INTERAKTIV MENYU
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 To'plamlar nazariyasi", callback_data="menu_sets")],
        [InlineKeyboardButton(text="🔢 Kombinatorika", callback_data="menu_comb")],
        [InlineKeyboardButton(text="🔗 Munosabatlar", callback_data="menu_rel")],
        [InlineKeyboardButton(text="📐 Mantiq", callback_data="menu_logic")],
        [InlineKeyboardButton(text="🕸️ Graflar", callback_data="menu_graph")],
        [InlineKeyboardButton(text="🚀 Eng qisqa yo'l (Dijkstra)", callback_data="menu_path")],
        [InlineKeyboardButton(text="✉️ Adminga murojaat yuborish", callback_data="menu_feedback")]
    ])

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Asosiy menyuga", callback_data="back_home")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id in waiting_for_feedback:
        waiting_for_feedback.remove(message.from_user.id)
        
    text = "✨ **Math Logic Helper** AI botiga xush kelibsiz! Savolingizni yozing yoki rasm yuboring:"
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def menu_handler(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    
    if action == "sets":
        text = "📌 **To'plamlar**\n\nFormat: `/sets 1,2,3 | 2,3,4 | 1,2,3,4,5`"
    elif action == "comb":
        text = "🔢 **Kombinatorika**\n\nFormat: `/comb 5 2`"
    elif action == "rel":
        text = "🔗 **Munosabatlar**\n\nFormat: `/rel 1,2,3 | 1-1 2-2 3-3 1-2`"
    elif action == "logic":
        text = "📐 **Mantiq**\n\nFormat: `/logic A and (not B)`"
    elif action == "graph":
        text = "🕸️ **Graflar**\n\nFormat: `/graph 1-2 2-3 3-1`"
    elif action == "path":
        text = "🚀 **Eng qisqa yo'l**\n\nFormat: `/path 1 4 | 1-2:5 2-3:1`"
    elif action == "feedback":
        waiting_for_feedback.add(callback.from_user.id)
        text = "✉️ **Adminga xabar yuborish**\n\nIltimos, murojaatingizni yoki savolingizni shu yerga yozib yuboring:"
        await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="Markdown")
        await callback.answer()
        return
        
    await callback.message.edit_text(text, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_home")
async def back_home_handler(callback: CallbackQuery):
    if callback.from_user.id in waiting_for_feedback:
        waiting_for_feedback.remove(callback.from_user.id)
        
    await callback.message.edit_text("✨ Asosiy menyu. Bo'limni tanlang:", reply_markup=get_main_menu(), parse_mode="Markdown")
    await callback.answer()

# ---------------------------------------------------------------- INTERACTIONS API ORQALI RASM VA MATN TUSHUNISHI
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    sent_msg = await message.answer("🔍 Rasm Interactions API orqali tahlil qilinmoqda...")
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")
        
        # Interactions API multimodal chaqiruvi
        interaction = client.interactions.create(
            model="gemini-4-hydrogen",
            input=[
                {"type": "text", "text": "Bu rasmdagi matematik yoki mantiqiy masalani o'qib, uni qadam-baqadam va tushunarli qilib o'zbek tilida yechib ber."},
                {
                    "type": "image",
                    "data": image_b64,
                    "mime_type": "image/jpeg"
                }
            ]
        )
        
        await bot.edit_message_text(interaction.output_text, chat_id=message.chat.id, message_id=sent_msg.message_id, reply_markup=get_main_menu())
    except Exception as e:
        await bot.edit_message_text(f"❌ Rasmni o'qishda xatolik: {e}", chat_id=message.chat.id, message_id=sent_msg.message_id, reply_markup=get_main_menu())

@dp.message()
async def handle_text_messages(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in waiting_for_feedback:
        waiting_for_feedback.remove(user_id)
        user_name = message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Kiritilmagan"
        
        admin_text = (
            "📩 **Yangi murojaat keldi!**\n\n"
            f"👤 **Foydalanuvchi:** {user_name}\n"
            f"🔗 **Username:** {username}\n"
            f"🆔 **ID:** `{user_id}`\n\n"
            f"💬 **Xabar:**\n{message.text}"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
            await message.answer("✅ Murojaatingiz adminga yuborildi!", reply_markup=get_main_menu())
        except Exception:
            await message.answer("❌ Xabarni yuborib bo'lmadi.")
        return

    sent_msg = await message.answer("🤖 Interactions API o'ylayapman...")
    try:
        # Interactions API matnli so'rovi
        interaction = client.interactions.create(
            model="gemini-4-hydrogen",
            input=message.text
        )
        await bot.edit_message_text(interaction.output_text, chat_id=message.chat.id, message_id=sent_msg.message_id, reply_markup=get_main_menu())
    except Exception as e:
        await bot.edit_message_text(f"❌ Xatolik: {e}", chat_id=message.chat.id, message_id=sent_msg.message_id, reply_markup=get_main_menu())

# Buyruqlar handlerlari
@dp.message(Command("sets"))
async def sets_cmd(message: types.Message):
    try:
        res = sets_solver(message.text.replace("/sets", "", 1).strip())
        await message.answer(f"```\n{res}\n```", parse_mode="Markdown", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(Command("comb"))
async def comb_cmd(message: types.Message):
    try:
        res = comb_solver(message.text.replace("/comb", "", 1).strip())
        await message.answer(f"```\n{res}\n```", parse_mode="Markdown", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(Command("rel"))
async def rel_cmd(message: types.Message):
    try:
        res = rel_solver(message.text.replace("/rel", "", 1).strip())
        await message.answer(f"```\n{res}\n```", parse_mode="Markdown", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(Command("logic"))
async def logic_cmd(message: types.Message):
    try:
        res = truth_table(message.text.replace("/logic", "", 1).strip())
        await message.answer(f"```\n{res}\n```", parse_mode="Markdown", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(Command("graph"))
async def graph_cmd(message: types.Message):
    try:
        res = graph_solver(message.text.replace("/graph", "", 1).strip())
        await message.answer(f"```\n{res}\n```", parse_mode="Markdown", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(Command("path"))
async def path_cmd(message: types.Message):
    try:
        res = path_solver(message.text.replace("/path", "", 1).strip())
        await message.answer(f"```\n{res}\n```", parse_mode="Markdown", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

if __name__ == "__main__":
    print("Interactions API asosidagi Bot ishga tushdi...")
    asyncio.run(dp.start_polling(bot))