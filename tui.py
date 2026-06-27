"""
TUI Navigation Engine — محرك التنقل التفاعلي للمعالج.
يدعم:
- التنقل بالأسهم ↑↓
- التأكيد بـ Enter
- التحديد المتعدد بـ Space (مسطرة المسافة)
- البحث بالكتابة
- الرجوع بـ Back / ESC

يعمل على Termux وأي طرفية تدعم ANSI.
يسقط تلقائياً لوضع الأرقام إن لم تتوفر قراءة المفاتيح الخام (raw mode).
"""
import sys
import os

# ألوان
R   = "\033[0m"
B   = "\033[1m"
DIM = "\033[2m"
G   = "\033[32m"
Y   = "\033[33m"
C   = "\033[36m"
RD  = "\033[31m"
O   = "\033[38;5;208m"
GRN = "\033[38;5;46m"

# نتائج خاصة
BACK   = "__BACK__"
CANCEL = "__CANCEL__"


def _supports_raw():
    """هل يمكن قراءة المفاتيح الخام؟ (يحتاج tty)."""
    try:
        import termios, tty  # noqa
        return sys.stdin.isatty()
    except Exception:
        return False


def _read_key():
    """يقرأ مفتاحاً واحداً (مع دعم الأسهم) في raw mode."""
    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":  # بداية تسلسل (سهم أو ESC)
            # حاول قراءة الباقي
            seq = sys.stdin.read(2)
            if seq == "[A": return "UP"
            if seq == "[B": return "DOWN"
            if seq == "[C": return "RIGHT"
            if seq == "[D": return "LEFT"
            return "ESC"
        if ch in ("\r", "\n"): return "ENTER"
        if ch == " ":          return "SPACE"
        if ch == "\t":         return "TAB"
        if ch == "\x7f":       return "BACKSPACE"
        if ch == "\x03":       raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _clear_lines(n):
    """يمسح n أسطر للأعلى (لإعادة الرسم)."""
    for _ in range(n):
        sys.stdout.write("\033[1A\033[2K")
    sys.stdout.flush()


def select(title, options, allow_back=True, hint=""):
    """
    قائمة اختيار واحد بالأسهم.
    options: list of (label, description) أو list of strings
    يُرجع: index المختار، أو BACK، أو CANCEL
    """
    opts = _normalize(options)
    if allow_back:
        opts = opts + [("⬅ رجوع", "للخطوة السابقة")]

    if not _supports_raw():
        return _select_numbered(title, opts, allow_back)

    idx = 0
    first = True
    n_lines = 0

    while True:
        if not first:
            _clear_lines(n_lines)
        first = False

        lines = []
        lines.append(f"\n  {O}{B}{title}{R}")
        if hint:
            lines.append(f"  {DIM}{hint}{R}")
        for i, (label, desc) in enumerate(opts):
            is_back = allow_back and i == len(opts) - 1
            if i == idx:
                arrow = f"{GRN}❯{R}"
                lbl   = f"{B}{GRN}{label}{R}"
            else:
                arrow = " "
                lbl   = f"{label}"
            d = f"  {DIM}{desc}{R}" if desc else ""
            lines.append(f"  {arrow} {lbl}{d}")
        lines.append(f"  {DIM}↑↓ تنقّل • Enter تأكيد" + ("  • ⬅ رجوع" if allow_back else "") + f"{R}")

        out = "\n".join(lines)
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
        n_lines = out.count("\n") + 1

        key = _read_key()
        if key == "UP":
            idx = (idx - 1) % len(opts)
        elif key == "DOWN":
            idx = (idx + 1) % len(opts)
        elif key == "ENTER":
            if allow_back and idx == len(opts) - 1:
                return BACK
            return idx
        elif key in ("ESC", "LEFT") and allow_back:
            return BACK
        elif key == "\x03":
            return CANCEL


def multi_select(title, options, allow_back=True):
    """
    قائمة اختيار متعدد. Space للتحديد، A لاختيار الكل، Enter للتأكيد.
    يُرجع: list من indexes المحددة، أو BACK، أو CANCEL
    """
    opts = _normalize(options)

    if not _supports_raw():
        return _multi_numbered(title, opts, allow_back)

    idx = 0
    selected = set()
    first = True
    n_lines = 0

    while True:
        if not first:
            _clear_lines(n_lines)
        first = False

        lines = []
        lines.append(f"\n  {O}{B}{title}{R}")
        for i, (label, desc) in enumerate(opts):
            box = f"{GRN}◉{R}" if i in selected else f"{DIM}◯{R}"
            if i == idx:
                arrow = f"{GRN}❯{R}"
                lbl   = f"{B}{label}{R}"
            else:
                arrow = " "
                lbl   = label
            d = f"  {DIM}{desc}{R}" if desc else ""
            lines.append(f"  {arrow} {box} {lbl}{d}")
        lines.append(f"  {DIM}↑↓ تنقّل • Space تحديد • A الكل • Enter تأكيد" + ("  • ⬅ رجوع (ESC)" if allow_back else "") + f"{R}")

        out = "\n".join(lines)
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
        n_lines = out.count("\n") + 1

        key = _read_key()
        if key == "UP":
            idx = (idx - 1) % len(opts)
        elif key == "DOWN":
            idx = (idx + 1) % len(opts)
        elif key == "SPACE":
            if idx in selected: selected.discard(idx)
            else: selected.add(idx)
        elif key in ("a", "A"):
            if len(selected) == len(opts): selected.clear()
            else: selected = set(range(len(opts)))
        elif key == "ENTER":
            return sorted(selected)
        elif key in ("ESC", "LEFT") and allow_back:
            return BACK
        elif key == "\x03":
            return CANCEL


# ── fallback: وضع الأرقام (إن لم يتوفر raw mode) ─────────────
def _select_numbered(title, opts, allow_back):
    print(f"\n  {O}{B}{title}{R}")
    for i, (label, desc) in enumerate(opts, 1):
        d = f"  {DIM}{desc}{R}" if desc else ""
        print(f"  {C}{i}{R}. {label}{d}")
    while True:
        try:
            v = input(f"  اختر [1]: ").strip()
            if not v:
                v = "1"
            n = int(v)
            if 1 <= n <= len(opts):
                if allow_back and n == len(opts):
                    return BACK
                return n - 1
        except (ValueError, KeyboardInterrupt, EOFError):
            return CANCEL


def _multi_numbered(title, opts, allow_back):
    print(f"\n  {O}{B}{title}{R}")
    for i, (label, desc) in enumerate(opts, 1):
        d = f"  {DIM}{desc}{R}" if desc else ""
        print(f"  {C}{i}{R}. {label}{d}")
    print(f"  {DIM}اكتب الأرقام مفصولة بفواصل (مثل 1,3) أو all{R}")
    try:
        v = input("  اختيارك: ").strip()
        if v.lower() == "all":
            return list(range(len(opts)))
        return [int(x)-1 for x in v.split(",") if x.strip().isdigit() and 0 < int(x) <= len(opts)]
    except (KeyboardInterrupt, EOFError):
        return CANCEL


def _normalize(options):
    """يحوّل القائمة لصيغة (label, desc)."""
    out = []
    for o in options:
        if isinstance(o, (tuple, list)):
            if len(o) >= 2:
                out.append((str(o[0]), str(o[1])))
            else:
                out.append((str(o[0]), ""))
        else:
            out.append((str(o), ""))
    return out
