import requests, warnings
from requests.packages import urllib3
from lxml import etree
import os
import re
import sys
import json
import time
import random
import argparse
import traceback
from urllib.parse import urlparse

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

# 开奖站点对默认的 python-requests UA 会返回拦截页，必须伪装 UA
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36',
]
TIMEOUT = (10, 25)          # (连接超时, 读取超时)
RETRIES = 3
PER_ATTEMPT_SECONDS = 60    # 单次请求的读取时长上限，防慢速滴流把任务拖死
TOTAL_BUDGET_SECONDS = 360  # 整个抓取过程的硬预算

_DEADLINE = [None]

def budgetLeft():
    if not _DEADLINE[0]:
        return None
    return _DEADLINE[0] - time.time()

def refererOf(url):
    # 用来源自身的站点根作为 Referer，避免在代码里写死具体域名
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return None
    return '{}://{}/'.format(p.scheme, p.netloc)

class _FatalHttpError(Exception):
    """不可重试的 HTTP 错误（如 404），直接放弃当前源。"""
    pass

def replaceStr(s=''):
    # 全角空格 / 千分位逗号都会污染 CSV 列，统一清洗
    return str(s).replace(' ', '').replace(',', '').replace('\u3000', '').strip()

def numberStr(s=''):
    """金额字段只保留数字。官网接口会给 '6250000（含加奖1250000）' 这种带说明的字符串，
    直接落盘会让下游按数字解析失败。"""
    s = replaceStr(s)
    m = re.match(r'^(\d+)', s)
    if m:
        return m.group(1)
    digits = re.sub(r'\D', '', s)
    return digits

def mkdir(path):
    path = path.strip()
    path = path.rstrip('\\')
    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)
        return True
    else:
        return False

def fetch(url, referer=None, retries=RETRIES):
    """带重试和硬性时间预算的 GET。
    用流式读取，边读边计时，避免对方慢速滴流时读超时永远不触发、任务被无限拖住。
    """
    if not url or not url.startswith(('http://', 'https://')):
        raise ValueError('invalid url: {!r}'.format(url))

    lastError = None
    for attempt in range(1, retries + 1):
        left = budgetLeft()
        if left is not None and left <= 5:
            raise RuntimeError('global time budget exhausted before attempt')
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        if referer:
            headers['Referer'] = referer
        try:
            with requests.get(url=url, headers=headers, timeout=TIMEOUT, verify=False, stream=True) as response:
                # 4xx 里只有 403/429 值得重试（多是反爬/限流），其余直接失败省时间
                if 400 <= response.status_code < 500 and response.status_code not in (403, 429):
                    raise _FatalHttpError('HTTP {} for {}'.format(response.status_code, url))
                # 状态码非 2xx 时抛异常，否则错误页会被静默解析成 0 条
                response.raise_for_status()

                body = bytearray()
                startedAt = time.time()
                for chunk in response.iter_content(chunk_size=65536):
                    body += chunk
                    if time.time() - startedAt > PER_ATTEMPT_SECONDS:
                        raise TimeoutError('response too slow, aborted after {}s and {} bytes'
                                           .format(PER_ATTEMPT_SECONDS, len(body)))
                if not body:
                    raise ValueError('empty body')
                # 回填已读内容，后续仍按普通 Response 使用
                response._content = bytes(body)
                response._content_consumed = True
                return response
        except _FatalHttpError:
            raise
        except Exception as e:
            lastError = '{}: {}'.format(type(e).__name__, e)
            print('fetch attempt {}/{} failed -> {}: {}'.format(attempt, retries, type(e).__name__, e))
            if attempt < retries:
                # 指数退避 + 抖动，避开同 IP / 同时间窗口的限流
                time.sleep(min(2 ** attempt, 10) + random.uniform(0.5, 1.5))
    raise RuntimeError('all {} attempts failed, last error: {}'.format(retries, lastError))

def fetchText(url):
    response = fetch(url, referer=refererOf(url))
    # 国内站点多是 GBK，requests 常猜成 ISO-8859-1，会让中文变成乱码
    if not response.encoding or response.encoding.lower() in ('iso-8859-1', 'ascii'):
        response.encoding = response.apparent_encoding or 'utf-8'
    return response.text

def buildVal(record):
    """把 (期号, 红球[], 蓝球, 一等奖, 二等奖, 开奖日期) 拼成一行 CSV。"""
    datetime, red, blue, prize1, prize2, drawdate = record
    cols = [datetime] + list(red) + [str(blue).strip(), numberStr(prize1), numberStr(prize2), str(drawdate).strip()]
    return '{}\n'.format(','.join(cols))

def storeRow(ssqs, datetime, val, onlyNew=False):
    """写入一行，返回是否算作更新。值异常 / 未变化都不算。"""
    if len(val) < 26:
        return 0
    if datetime in ssqs and (onlyNew or ssqs[datetime] == val):
        return 0
    ssqs[datetime] = val
    return 1

def parseCwlRecord(i):
    """福彩官网 result[] 结构的字段映射。"""
    datetime = str(i["code"])[2:]
    red = str(i['red']).split(',')
    blue = str(i['blue']).strip()
    prize1 = i['prizegrades'][0]['typemoney']
    prize2 = i['prizegrades'][1]['typemoney']
    drawdate = str(i["date"])[0:len(str(i["date"])) - 3]
    return datetime, red, blue, prize1, prize2, drawdate

def parseZhcwRecord(i):
    """中彩网 data[] 结构的字段映射（期号 7 位，红球用空格分隔）。"""
    datetime = str(i['issue'])[2:]
    red = str(i['frontWinningNum']).split()
    blue = str(i['backWinningNum']).strip()
    grades = {}
    for g in (i.get('winnerDetails') or []):
        base = g.get('baseBetWinner') or {}
        grades[str(g.get('awardEtc'))] = base.get('awardMoney', '')
    prize1 = grades.get('1', '')
    prize2 = grades.get('2', '')
    drawdate = str(i['openTime']).strip()
    return datetime, red, blue, prize1, prize2, drawdate

def parseTxtLine(line):
    """纯文本数据行的字段映射。
    列：期号 日期 红1-6 蓝 红排序... 销售额 奖池 一等奖注数 一等奖金额 二等奖注数 二等奖金额 ...
    """
    parts = line.split()
    if len(parts) < 21:
        return None
    issue = parts[0]
    if not issue.isdigit() or len(issue) < 7:
        return None
    datetime = issue[2:]
    red = parts[2:8]
    blue = parts[8]
    drawdate = parts[1]
    if not all(x.isdigit() for x in red + [blue]):
        return None
    prize1 = parts[18]
    prize2 = parts[20]
    return datetime, red, blue, prize1, prize2, drawdate

def collectFromJsonBody(payload, ssqs, label, onlyNew=False):
    records = None
    parser = None
    if isinstance(payload, dict) and isinstance(payload.get('result'), list):
        records, parser = payload['result'], parseCwlRecord
    elif isinstance(payload, dict) and isinstance(payload.get('data'), list):
        records, parser = payload['data'], parseZhcwRecord
    if not records:
        print('WARNING {} returned no records (keys: {}), source may be broken \n'
              .format(label, list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__))
        return 0, 0

    rows = 0
    updates = 0
    for i in records:
        try:
            record = parser(i)
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            print('Skipped a malformed record from {} \n'.format(label))
            continue
        if len(record[0]) < 5:
            continue
        rows = rows + 1
        updates = updates + storeRow(ssqs, record[0], buildVal(record), onlyNew)

    print('{} rows = {}, updateSum = {} \n'.format(label, rows, updates))
    return rows, updates

def collectFromHtmlBody(text, ssqs, label):
    selector = etree.HTML(text)
    if selector is None:
        print('WARNING {} page is not valid HTML \n'.format(label))
        return 0, 0
    trs = selector.xpath('//tr[@class="t_tr1"]')
    if not trs:
        print('WARNING {} page has no t_tr1 rows, maybe blocked or layout changed \n'.format(label))
        return 0, 0

    rows = 0
    updates = 0
    for i in trs:
        try:
            tds = i.xpath('td/text()')
            record = (replaceStr(tds[0]), [replaceStr(x) for x in tds[1:7]],
                      replaceStr(tds[7]), replaceStr(tds[11]), replaceStr(tds[13]), replaceStr(tds[15]))
        except (KeyError, IndexError, TypeError, AttributeError):
            # 列数变化时跳过该行，不要让整个源挂掉
            print('Skipped a malformed row from {} \n'.format(label))
            continue
        if len(record[0]) < 5:
            continue
        rows = rows + 1
        updates = updates + storeRow(ssqs, record[0], buildVal(record))

    print('{} rows = {}, updateSum = {} \n'.format(label, rows, updates))
    return rows, updates

def collectFromTextBody(text, ssqs, label, onlyNew=False):
    rows = 0
    updates = 0
    for line in text.splitlines():
        record = parseTxtLine(line.strip())
        if not record:
            continue
        if len(record[0]) < 5:
            continue
        rows = rows + 1
        updates = updates + storeRow(ssqs, record[0], buildVal(record), onlyNew)

    if rows == 0:
        print('WARNING {} returned no parsable rows, source may be broken \n'.format(label))
    print('{} rows = {}, updateSum = {} \n'.format(label, rows, updates))
    return rows, updates

def collectFromAny(url, ssqs, label, onlyNew=False):
    """抓一个源并自动识别格式：JSON / HTML 表格 / 纯文本。
    只认内容不认地址，换源时不用改代码。
    """
    try:
        text = fetchText(url)
    except Exception as e:
        print('Failed requests error, {}={} \n{}: {} \n'.format(label, url, type(e).__name__, e))
        return 0, 0

    head = text.lstrip()[:1]
    try:
        if head in ('{', '['):
            return collectFromJsonBody(json.loads(text), ssqs, label, onlyNew)
        if '<tr' in text or '<table' in text:
            return collectFromHtmlBody(text, ssqs, label)
        return collectFromTextBody(text, ssqs, label, onlyNew)
    except Exception as e:
        print('Parse failed, {}={} \n{}: {} \n'.format(label, url, type(e).__name__, e))
        return 0, 0

def start(url, url2, url3=''):
    _DEADLINE[0] = time.time() + TOTAL_BUDGET_SECONDS
    ssqPath = './spider_data/ssq.txt'
    ssqJSPath = './spider_data/ssq.js'
    ssqs = {}
    historyExists = True

    try:
        oldFile = open(ssqPath, 'r')
        try:
            line = oldFile.readline()
            while line:
                ssqs[line.split(',')[0]] = line
                line = oldFile.readline()
        finally:
            oldFile.close()
    except IOError:
        historyExists = False
        print('Failed to read history, {} isNotExists \n'.format(ssqPath))

    rowsFromUrl2 = 0
    rowsFromUrl = 0
    rowsFromFallback = 0
    updatesTotal = 0

    # 源1：主源（全量历史，重量级）
    if url and (budgetLeft() is None or budgetLeft() > 10):
        try:
            rowsFromUrl, updates = collectFromAny(url, ssqs, 'url')
            updatesTotal = updatesTotal + updates
        except Exception as e:
            print('Source url crashed, keep going: {}: {} \n'.format(type(e).__name__, e))

    # 源2：附加源（一般是轻量接口，每次运行都取，只补新期号）
    if url2 and (budgetLeft() is None or budgetLeft() > 10):
        try:
            rowsFromUrl2, updates = collectFromAny(url2, ssqs, 'url2', onlyNew=True)
            updatesTotal = updatesTotal + updates
        except Exception as e:
            print('Source url2 crashed, keep going: {}: {} \n'.format(type(e).__name__, e))

    # 源3：兜底源，只在主源拿不到数据时启用
    url2Host = urlparse(url2).netloc if url2 else ''
    url3Host = urlparse(url3).netloc if url3 else ''
    if ((not url) or (url and rowsFromUrl == 0)) and (budgetLeft() is None or budgetLeft() > 10):
        if not url3:
            print('No fallback url configured (-u3), skip \n')
        elif url2Host and url3Host and url2Host == url3Host:
            print('Fallback source is the same as url2, skip \n')
        else:
            print('Activating fallback source \n')
            try:
                rowsFromFallback, updates = collectFromAny(url3, ssqs, 'fallback', onlyNew=True)
                updatesTotal = updatesTotal + updates
            except Exception as e:
                print('Source fallback crashed, keep going: {}: {} \n'.format(type(e).__name__, e))

    totalRows = rowsFromUrl2 + rowsFromUrl + rowsFromFallback
    print('rows parsed: url={}, url2={}, fallback={} \n'.format(rowsFromUrl, rowsFromUrl2, rowsFromFallback))

    # 所有源都没拿到数据，说明是抓取故障而不是「暂无新开奖」
    if totalRows == 0:
        print('All sources returned no rows, aborting without touching data files \n')
        return False

    # 历史文件缺失且只抓到很少数据时，宁可不写，避免把完整历史覆盖成残缺文件
    validRows = len([k for k in ssqs.keys() if len(k) == 5 and k.isdigit()])
    if not historyExists and validRows < 500:
        print('Refuse to overwrite: only {} rows collected while history is missing \n'.format(validRows))
        return False

    # 期号断层预警
    gaps = findGaps(ssqs)
    if gaps:
        print('WARNING missing issues detected: {} \n'.format(gaps))

    # 内容没变就不写盘，避免定时任务产生空提交和无意义的文件改动
    if not ssqChanged(ssqPath, ssqs):
        print('No data change, skip writing \n')
        return True

    timeMark = '999999999'
    ssqs[timeMark] = '{},{},{},{},{}\n'.format(timeMark, updatesTotal, validRows + 1, str(int(round(time.time() * 1000))), 'Current behavior update info')
    ssqkeys = sorted(ssqs.keys(), reverse=True)
    # 先在内存里拼好，避免写入中途失败把已有数据截断成空文件
    txtBody = ''.join(ssqs[key] for key in ssqkeys)
    jsBody = 'window.ssqData = `{}`'.format(txtBody)
    try:
        mkdir('./spider_data/')
        writeAtomic(ssqPath, txtBody)
        writeAtomic(ssqJSPath, jsBody)
        print('updateSum is {} \n'.format(updatesTotal))
    except IOError as e:
        print('Write failed, {}: {} \n'.format(type(e).__name__, e))
        return False

    return True

def ssqChanged(ssqPath, ssqs):
    """比较抓到的数据与磁盘文件是否一致（忽略 999999999 统计行）。"""
    try:
        with open(ssqPath, 'r') as f:
            oldLines = {}
            for line in f:
                key = line.split(',')[0]
                if key and key != '999999999':
                    oldLines[key] = line
    except IOError:
        return True

    newLines = dict((k, v) for k, v in ssqs.items() if k != '999999999')
    return oldLines != newLines

def writeAtomic(path, content):
    # 同目录临时文件 + os.replace，保证要么是旧内容要么是新内容
    tmpPath = '{}.tmp'.format(path)
    f = open(tmpPath, 'w')
    try:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    finally:
        f.close()
    os.replace(tmpPath, path)

def findGaps(ssqs):
    # 按 5 位期号的年份分组，报出组内缺失的期号
    issues = {}
    for key in ssqs.keys():
        if len(key) != 5 or not key.isdigit():
            continue
        issues.setdefault(key[0:2], []).append(int(key[2:]))
    gaps = []
    for year in sorted(issues.keys()):
        nums = set(issues[year])
        for n in range(min(nums), max(nums) + 1):
            if n not in nums:
                gaps.append('{}{:03d}'.format(year, n))
    return gaps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", type=str, required=False, default="", help="主源")
    parser.add_argument("-u2", "--url2", type=str, required=False, default="", help="附加源")
    parser.add_argument("-u3", "--url3", type=str, required=False, default="", help="兜底源")
    args = parser.parse_args()
    try:
        print(args)
        # URL 两端的空白会让 requests 直接报错，先清掉
        ok = start(args.url.strip(), args.url2.strip(), args.url3.strip())
        print('Finished')
        if not ok:
            sys.exit(1)
    except Exception:
        # 打完整堆栈并以非 0 退出，否则 CI 会把静默失败当成功
        traceback.print_exc()
        print('error')
        sys.exit(1)
