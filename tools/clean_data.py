"""
清洗谜题数据中的抓取残留 / 切割错误。

同一份 clean() 逻辑作用于两处，保证 txt 与 db 一致：

    python tools/clean_data.py --txt              # 重写 origin_data/*.txt
    python tools/clean_data.py --db data/x.db     # 修正已有数据库
    加 --apply 才真正写入，默认只预览。
"""
import argparse
import hashlib
import os
import re
import sqlite3
import sys

DATA_DIR = "origin_data"
FILES = ["riddle.txt", "joke.txt", "idiom.txt", "brain_teaser.txt",
         "trivia.txt", "word_puzzle.txt"]

MAX_ANSWER = 500
MAX_QUESTION = 200

# 抓取残留标记：HTML 片段混进正文
GARBAGE = re.compile(r'/pic/|</?[a-z]+>|&nbsp')
# 连续 ASCII 连字符：会被误认成分隔符。单个 '-' 不动（"-273.15"、"Wi-Fi"）
HYPHEN_RUN = re.compile(r'-{2,}')
# 答案里粘上了下一条的开头。
# 编号必须是 1~2 位且后面接汉字，否则会误伤 "IEEE 802.11" / "USB 1.0" 这类正文。
MERGE_MARK = re.compile(r'=\s*>|＝>|\s+\d{1,2}\s*[.、]\s*[一-鿿]')
# "答案：" 只在前面出现过问号时才当作粘连，
# 否则会误伤 "按照不同标准有不同答案：…" 这类正文。
MERGE_ANSWER = re.compile(r'[?？][^?？]*?(答案\s*[：:])')
# 被 MERGE_MARK 截断后，尾部残留的下一条问句
TRAIL_Q = re.compile(r'[\s，。、；！?？)）】\]]+[^。！\n]{0,40}[?？]\s*$')
# 只删首尾明显的残缺符号，句末标点（。！？…）一律保留，避免大面积无意义改写
LEAD_JUNK = '　 \t·—~～*>＞:：,，;；、'      # 不含 '-'，否则 "-273.15" 会掉负号
TAIL_JUNK = '　 \t—-－~～*>＞'
OPEN_BRACKET = '（(【[{「《'
CLOSE_BRACKET = '）)】]}」》'


def _strip_junk(s):
    s = s.replace('[答案]', '').replace('【答案】', '')
    prev = None
    while s and s != prev:
        prev = s
        s = s.lstrip(LEAD_JUNK).rstrip(TAIL_JUNK)
        if s and s[0] in CLOSE_BRACKET:
            s = s[1:]
        if s and s[-1] in OPEN_BRACKET:        # 结尾的左括号一定是残缺
            s = s[:-1]
        elif s and s[-1] in CLOSE_BRACKET:     # 结尾的右括号只在没配对时去掉
            if OPEN_BRACKET[CLOSE_BRACKET.index(s[-1])] not in s[:-1]:
                s = s[:-1]
    return s


def _is_empty(s):
    """去掉空白与 ASCII 标点后没内容。π、♂、ＣＤ 这类算有内容。"""
    return not re.sub(r'[\s\x21-\x2f\x3a-\x40\x5b-\x60\x7b-\x7e]', '', s)


def clean(question, answer):
    """返回 (question, answer)；无法修复则返回 None。"""
    if GARBAGE.search(question) or GARBAGE.search(answer):
        return None

    # 正文里的 "--" / "---" 会被当成条目分隔符，换成全角破折号（见 CLAUDE.md）
    question = HYPHEN_RUN.sub('——', question)
    answer = HYPHEN_RUN.sub('——', answer)

    # 括号被切断在问题末尾、答案以拼音注音开头 → 原始切割就废了，修不回来
    if re.search(r'[（(][^）)]*$', question) and re.match(r'[a-z]', answer):
        return None

    note = ''
    head, sep, tail = answer.partition('\n注释')
    if sep:                                    # 谜语的小贴士，原样保留
        answer, note = head, sep + tail

    m = MERGE_MARK.search(answer) or MERGE_ANSWER.search(answer)
    if m:                                      # 只在确实截断过时才清尾部问句
        cut = m.start(1) if m.re is MERGE_ANSWER else m.start()
        answer = _strip_junk(answer[:cut])
        answer = _strip_junk(TRAIL_Q.sub('', answer))
        if answer.endswith(('?', '？')):        # 截完还是个问句 → 整条已残缺
            return None
    else:
        answer = _strip_junk(answer)

    question = _strip_junk(question)

    if _is_empty(question) or _is_empty(answer):
        return None
    if len(question) > MAX_QUESTION or len(answer) > MAX_ANSWER:
        return None
    return question, answer + note


def md5(question, answer):
    return hashlib.md5(f"{question}|{answer}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# 供 tools/ 下各采集脚本复用的唯一写入入口。
# 各脚本原来自己拼 "问题：…\n答案:…"，其中 12 个把 "---\n" 写在条目 *之前*，
# 一旦已有文件不以换行结尾就会粘成 "答案:料---"。统一走这里，顺带过一遍 clean()。
# ---------------------------------------------------------------------------

def load_hashes(path):
    """读已有 txt 的 content_hash 集合，切割规则与 init_db.py 保持一致。"""
    hashes = set()
    if not os.path.exists(path):
        return hashes
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    for chunk in re.split(r'-{3,}', raw):
        m = re.match(r'\s*问题[：:](.*?)[\r\n]+答案[：:](.*)', chunk, re.DOTALL)
        if m:
            q, a = m.group(1).strip(), m.group(2).strip()
            if q and a:
                hashes.add(md5(q, a))
    return hashes


def append_entries(path, pairs, existing_hashes=None):
    """追加 (question, answer) 到 txt：先 clean()，再按 hash 去重，返回新增条数。

    分隔符一律写在条目之后（"…\\n---\\n"），并在追加前补齐缺失的换行，
    这样无论已有文件什么状态都不会把 "---" 粘到答案行末。
    """
    if existing_hashes is None:
        existing_hashes = load_hashes(path)

    # 已有文件的最后一条可能既缺换行又缺分隔符，两种都要补上
    prefix = ''
    size = os.path.getsize(path) if os.path.exists(path) else 0
    if size:
        with open(path, 'rb') as f:
            f.seek(max(0, size - 64))
            tail = f.read().decode('utf-8', 'ignore')
        if not tail.rstrip().endswith('---'):
            prefix = '---\n' if tail.endswith('\n') else '\n---\n'

    added = 0
    with open(path, 'a', encoding='utf-8') as f:
        if prefix:
            f.write(prefix)
        for q, a in pairs:
            result = clean(q, a)
            if result is None:
                continue
            q, a = result
            h = md5(q, a)
            if h in existing_hashes:
                continue
            existing_hashes.add(h)
            f.write(f"问题：{q}\n答案:{a}\n---\n")
            added += 1
    return added


def _preview(label, rows, limit=40):
    print(f"\n### {label}: {len(rows)}")
    for r in rows[:limit]:
        print("  " + r)
    if len(rows) > limit:
        print(f"  ... 还有 {len(rows) - limit} 条")


def clean_txt(apply_):
    total_removed = total_changed = 0
    for name in FILES:
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            raw = f.read()

        removed, changed, kept = [], [], []
        for chunk in re.split(r'-{3,}', raw):
            chunk = chunk.strip()
            if not chunk:
                continue
            m = re.match(r'问题[：:](.*?)[\r\n]+答案[：:](.*)', chunk, re.DOTALL)
            if not m:
                removed.append(chunk[:80].replace('\n', ' ⏎ '))
                continue
            q, a = m.group(1).strip(), m.group(2).strip()
            res = clean(q, a)
            if res is None:
                removed.append(f"{q[:40]} | {a[:60]}".replace('\n', ' ⏎ '))
                continue
            nq, na = res
            if (nq, na) != (q, a):
                changed.append(f"{q[:36]} | {a[:50]} → {nq[:36]} | {na[:50]}".replace('\n', ' ⏎ '))
            kept.append((nq, na))

        print(f"\n=== {name}: {len(kept)} 保留 / {len(removed)} 删除 / {len(changed)} 修正")
        _preview("删除", removed, 25)
        _preview("修正", changed, 25)
        total_removed += len(removed)
        total_changed += len(changed)

        if apply_:
            body = ''.join(f"问题：{q}\n答案:{a}\n---\n" for q, a in kept)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(body)
    print(f"\n合计: 删除 {total_removed} / 修正 {total_changed}"
          f"{'（已写入）' if apply_ else '（预览，加 --apply 生效）'}")


def clean_db(db_path, apply_):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "select id, question, answer, content_hash from data_entries").fetchall()
    hashes = {h for _, _, _, h in rows}

    deletes, updates, dupes = [], [], []
    for rid, q, a, h in rows:
        res = clean(q, a)
        if res is None:
            deletes.append((rid, f"#{rid} {q[:40]} | {a[:60]}".replace('\n', ' ⏎ ')))
            continue
        nq, na = res
        if (nq, na) == (q, a):
            continue
        nh = md5(nq, na)
        if nh != h and nh in hashes:           # 修正后与已有条目重复
            dupes.append((rid, f"#{rid} {q[:40]} → 与已有条目重复"))
            continue
        hashes.discard(h)
        hashes.add(nh)
        updates.append((rid, nq, na, nh,
                        f"#{rid} {a[:50]} → {na[:50]}".replace('\n', ' ⏎ ')))

    print(f"\n=== {db_path}: {len(rows)} 行")
    _preview("删除（无法修复）", [d[1] for d in deletes])
    _preview("删除（修正后重复）", [d[1] for d in dupes])
    _preview("修正", [u[4] for u in updates])

    if apply_:
        ids = [d[0] for d in deletes] + [d[0] for d in dupes]
        conn.executemany("delete from data_entries where id=?", [(i,) for i in ids])
        conn.executemany(
            "update data_entries set question=?, answer=?, content_hash=? where id=?",
            [(u[1], u[2], u[3], u[0]) for u in updates])
        conn.commit()
        print(f"\n已写入：删除 {len(ids)} / 修正 {len(updates)}，"
              f"剩余 {conn.execute('select count(*) from data_entries').fetchone()[0]} 行")
    else:
        print(f"\n合计: 删除 {len(deletes) + len(dupes)} / 修正 {len(updates)}（预览，加 --apply 生效）")
    conn.close()


def _demo_append():
    """append_entries 自检：缺换行的旧文件不能把 --- 粘到答案行末。"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'x.txt')
        with open(p, 'w', encoding='utf-8') as f:
            f.write("问题：一斗米\n答案:料")          # 故意不以换行结尾
        assert append_entries(p, [("半坛酒", "酝"), ("一斗米", "料")]) == 1   # 后者去重
        body = open(p, encoding='utf-8').read()
        assert "答案:料---" not in body, body
        assert load_hashes(p) == {md5("一斗米", "料"), md5("半坛酒", "酝")}
        assert append_entries(p, [("脏的", "./pic/p>")]) == 0   # clean() 拦下
        # 已经以 --- 结尾时不再重复补分隔符
        assert append_entries(p, [("三分利", "刺")]) == 1
        assert '\n---\n---\n' not in open(p, encoding='utf-8').read()


def demo():
    """最小自检：每条规则一个样例。"""
    assert clean("四分钟./pic/p>　　2、剪刀", "吃馒头") is None
    assert clean("座中无人", "<") is None
    assert clean("木字多一撇", "(") is None
    # 非 ASCII 的单字符答案是合法的，不能删
    assert clean("怎样用三根筷子搭成比三大比四小的数？", "π")[1] == "π"
    # 拼音注音被切成两半 → 删；大写字母答案是正常的 → 留
    assert clean("腰里插笊篱（zh", "o li捞取东西的用具") is None
    assert clean("什么英文字母最多人喜欢听呢? (", "CD") == ("什么英文字母最多人喜欢听呢?", "CD")
    assert clean("什么英文字母最多人喜欢听呢", "ＣＤ")[1] == "ＣＤ"
    # 句末标点、结尾问句、省略号都不动
    assert clean("老师问：请用的地得造句。", "小明说：我的地得种了。") \
        == ("老师问：请用的地得造句。", "小明说：我的地得种了。")
    assert clean("我对理发师说：给我剪短一点", "理发师：这不是短了一点吗？")[1] == "理发师：这不是短了一点吗？"
    assert clean("大和尚对小和尚说了什么？", "从前有座山……")[1] == "从前有座山……"
    assert clean("什么东西比乌鸦更讨厌? (",
                 "乌鸦嘴) 14.孔子是我国最伟大的什么家? (答案：老人家") == ("什么东西比乌鸦更讨厌?", "乌鸦嘴")
    assert clean("一个自讨苦吃的地方在哪里", "药店 最不听话的是谁? 答案：聋子") == ("一个自讨苦吃的地方在哪里", "药店")
    assert clean("不小心溺水时，若附近沒有其他人该如何自救", "把水喝光=>但是还是会胀死")[1] == "把水喝光"
    assert clean("「狼来了！」这个故事给人有什么启示？[答案]", "同一大话只能重复两次") \
        == ("「狼来了！」这个故事给人有什么启示？", "同一大话只能重复两次")
    # 合法内容不动
    assert clean("猴子不喜欢什么线？", "平行线(因为没有相交<香蕉>)") \
        == ("猴子不喜欢什么线？", "平行线(因为没有相交<香蕉>)")   # 配对括号不动
    assert clean("两个兄弟一般长", "筷子\n注释:小贴士：筷子，古称箸。") \
        == ("两个兄弟一般长", "筷子\n注释:小贴士：筷子，古称箸。")
    assert clean("恐龙生活在什么时代？", "中生代（侏罗纪、白垩纪等）") \
        == ("恐龙生活在什么时代？", "中生代（侏罗纪、白垩纪等）")
    assert clean("什么是费马大定理？", "费马大定理指出n>2时，方程x^n+y^n=z^n没有正整数解")[1].startswith("费马")
    _demo_append()
    # 正文里的数字/编号不能当成粘连标记
    assert clean("什么是Wi-Fi？", "基于IEEE 802.11标准的无线网络技术")[1].endswith("技术")
    assert clean("什么是USB？", "从USB 1.0发展到USB4")[1].endswith("USB4")
    assert clean("绝对零度是多少？", "-273.15摄氏度")[1] == "-273.15摄氏度"
    assert clean("什么是Wi-Fi技术", "无线网络")[0] == "什么是Wi-Fi技术"
    # 正文里的 -- / --- 必须中和，否则污染分隔符
    assert clean("甲说A", "乙说B---丙说C") == ("甲说A", "乙说B——丙说C")
    assert clean("甲说A", "乙说B--丙说C") == ("甲说A", "乙说B——丙说C")
    assert clean("什么是斐波那契数列？", "每个数是前两个数之和：1,1,2,3,5,8,13...")[1].endswith("13...")
    assert clean("人体最强壮的肌肉是什么？", "按照不同标准有不同答案：咬肌咬合力最大")[1].endswith("最大")
    print("demo ok")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--txt", action="store_true")
    p.add_argument("--db")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()
    if args.demo:
        demo()
    elif args.txt:
        clean_txt(args.apply)
    elif args.db:
        clean_db(args.db, args.apply)
    else:
        p.print_help()
        sys.exit(1)
