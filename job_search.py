import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ========= 通用请求设置 =========

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session()
session.headers.update(DEFAULT_HEADERS)

# ========= 过滤规则 =========

INCLUDE_KEYWORDS = [
    "research",
    "researcher",
    "scientist",
    "machine learning",
    "deep learning",
    "ai engineer",
    "ml engineer",
    "research engineer",
    "nlp",
    "natural language",
    "llm",
    "multimodal",
    "generative",
    "diffusion",
    "reinforcement learning",
    "rlhf",
    "preference learning",
    "tokenization",
    "foundation model",
    "computer vision",
]

EXCLUDE_KEYWORDS = [
    "lead",
    "manager",
    "head",
    "principal",
    "director",
    "architect",
    "vp",
    "senior vice",
    "consultant",
    "intern",
    "internship",
    "student",
]

# 排除中国公司 / 地点相关
EXCLUDE_COMPANY_KEYWORDS = [
    "china",
    "beijing",
    "shanghai",
    "shenzhen",
    "alibaba",
    "tencent",
    "bytedance",
    "huawei",
    "byte dance",
]

# ==== 排除强制不适合的岗位 ====
EXCLUDE_HARD = [
    "postdoc",
    "post-doctoral",
    "post doctoral",
    "phd only",
    "requires phd",
    "phd required",
    "assistant professor",
    "associate professor",
    "professor",
    "faculty",
    "audio",
    "speech recognition",
    "tts",
    "biomedical",
    "molecular",
    "diagnostics",
    "clinical",
    "healthcare",
    "intern",
    "internship",
]

REMOTE_KEYWORDS = [
    "remote",
    "hybrid",
    "flexible",
    "work from home",
    "wfh",
    "remote-friendly",
    "remote friendly",
]


def is_relevant_job(title, company, location, snippet=""):
    text = " ".join([title or "", company or "", location or "", snippet or ""]).lower()

    # 1️⃣ 硬排除
    if any(k in text for k in EXCLUDE_HARD):
        return False

    # 2️⃣ 必须命中方向关键字
    if not any(k in text for k in INCLUDE_KEYWORDS):
        return False

    # 3️⃣ 排除管理岗等
    if any(k in text for k in EXCLUDE_KEYWORDS):
        return False

    # 4️⃣ 排除国内公司
    if any(k in text for k in EXCLUDE_COMPANY_KEYWORDS):
        return False

    return True


def detect_remote(location, snippet=""):
    text = " ".join([location or "", snippet or ""]).lower()
    return any(k in text for k in REMOTE_KEYWORDS)


def safe_get(url, **kwargs):
    """统一 GET 封装：自动带 headers，失败打印 warning。"""
    try:
        resp = session.get(url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:  # pragma: no cover - 网络异常
        print(f"[WARN] 请求失败 {url}: {e}")
        return None


def safe_post(url, json=None, **kwargs):
    """统一 POST 封装：针对 NTU/Workday 这类接口，失败也不要让程序崩。"""
    try:
        resp = session.post(url, json=json, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:  # pragma: no cover - 网络异常
        print(f"[WARN] POST失败 {url}: {e}")
        return None


# ========= 各站点抓取函数 =========


def fetch_mistral_jobs():
    """
    Mistral AI 官方 jobs（Lever 页面）
    """
    url = "https://jobs.lever.co/mistral"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for posting in soup.select("div.posting"):
        title_tag = posting.select_one("h5")
        location_tag = posting.select_one("span.sort-by-location")
        link_tag = posting.select_one("a.posting-btn-submit")

        if not (title_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        location = location_tag.get_text(strip=True) if location_tag else ""
        link = link_tag.get("href")
        company = "Mistral AI"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "Mistral",
            }
        )

    return jobs


def fetch_aisingapore_jobs():
    """
    AI Singapore 官方 careers 页面，抓取跳转到 NUS 的岗位。
    """
    url = "https://aisingapore.org/home/careers/"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for h2 in soup.select("h2"):
        a = h2.find("a", href=True)
        if not a:
            continue

        link = a["href"]
        if "careers.nus.edu.sg" not in link:
            continue  # 只要真正的职位链接

        title = a.get_text(strip=True)
        company = "AI Singapore / NUS"
        location = "Singapore"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": False,
                "link": link,
                "source": "AI Singapore",
            }
        )

    return jobs


def fetch_astar_jobs():
    """
    A*STAR Job Listing 页面，使用简单的文本过滤 AI/ML 相关岗位。
    """
    base_url = "https://careers.a-star.edu.sg/JobListing.aspx"
    resp = safe_get(base_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='JobDetails.aspx']"):
        title = a.get_text(strip=True)
        row_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        location = "Singapore"
        company = "A*STAR"

        if not is_relevant_job(title, company, location, snippet=row_text):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": False,
                "link": urljoin(base_url, a["href"]),
                "source": "A*STAR",
            }
        )

    return jobs


def fetch_sit_jobs():
    """
    Singapore Institute of Technology 职位搜索（Research Engineer）
    """
    url = "https://careers.singaporetech.edu.sg/search/?createNewAlert=false&q=Research+Engineer&locationsearch="
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a.jobTitle-link"):
        title = a.get_text(strip=True)
        link = urljoin("https://careers.singaporetech.edu.sg", a["href"])
        company = "Singapore Institute of Technology"
        location = "Singapore"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": False,
                "link": link,
                "source": "SIT",
            }
        )

    return jobs


def fetch_mycareersfuture_jobs():
    """
    MyCareersFuture: 搜索 research engineer，按新发职位排序。
    """
    url = "https://www.mycareersfuture.gov.sg/search?search=research%20engineer&sortBy=new_posting_date"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for card in soup.select("a[data-testid='job-card-link']"):
        title = card.get_text(strip=True)
        link = urljoin("https://www.mycareersfuture.gov.sg", card["href"])

        parent = card.find_parent("div") or card

        company_tag = parent.select_one("[data-testid='company-hire-info']")
        location_tag = parent.select_one("[data-testid='job-location']")

        company = company_tag.get_text(strip=True) if company_tag else "Unknown"
        location = location_tag.get_text(strip=True) if location_tag else "Singapore"

        snippet = parent.get_text(" ", strip=True)

        if not is_relevant_job(title, company, location, snippet=snippet):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location, snippet),
                "link": link,
                "source": "MyCareersFuture",
            }
        )

    return jobs


def fetch_anthropic_remote_jobs():
    """
    Anthropic 官方 jobs 页面，抓取 Research / ML 相关岗位（部分 Remote-Friendly）。
    """
    url = "https://www.anthropic.com/jobs"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for h3 in soup.find_all("h3"):
        title = h3.get_text(strip=True)
        if not any(
            k in title.lower()
            for k in ["research", "ml", "machine learning", "scientist", "engineer"]
        ):
            continue

        loc_tag = h3.find_next_sibling()
        location = loc_tag.get_text(strip=True) if loc_tag else ""

        apply_link = None
        for a in h3.find_all_next("a", string=lambda s: s and "Apply Now" in s):
            apply_link = a
            break
        if not apply_link or not apply_link.get("href"):
            continue

        company = "Anthropic"

        if not is_relevant_job(title, company, location):
            continue

        is_remote = detect_remote(location)

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": is_remote,
                "link": apply_link["href"],
                "source": "Anthropic",
            }
        )

    return jobs


def fetch_nus_jobs():
    """
    NUS careers portal (SmartRecruiters)
    抓取 Research / AI / ML 岗位
    """
    url = "https://careers.nus.edu.sg/careers"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # 兼容两种结构：class 和 data-automation-id
    for card in soup.select("a.job-title, a[data-automation-id='jobTitle']"):
        title = card.get_text(strip=True)
        link = card.get("href")
        if not link:
            continue
        link = urljoin(url, link)

        if not any(
            k in title.lower()
            for k in [
                "research",
                "scientist",
                "ai",
                "machine",
                "deep",
                "learning",
                "nlp",
                "intelligence",
                "computer vision",
                "engineer",
            ]
        ):
            continue

        company = "NUS"
        location = "Singapore"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": False,
                "link": link,
                "source": "NUS Careers",
            }
        )

    return jobs


def fetch_ntu_jobs():
    """
    NTU Careers (Workday) – 用 HTML 解析 job 列表，避免调 JSON API 报 400。
    入口页: https://ntu.wd3.myworkdayjobs.com/en-US/Careers
    """
    url = "https://ntu.wd3.myworkdayjobs.com/en-US/Careers"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # Workday 的职位标题一般是 <a data-automation-id="jobTitle">
    for a in soup.select("a[data-automation-id='jobTitle']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = a.get("href")
        if not link:
            continue
        link = urljoin(url, link)

        # 往上找一层大一点的 job 容器，拿点上下文当 snippet
        job_container = a.find_parent("div")
        snippet = job_container.get_text(" ", strip=True) if job_container else ""

        company = "NTU"
        location = "Singapore"

        # 过滤一遍，尽量只保留 AI / ML / Research 相关岗位
        if not is_relevant_job(title, company, location, snippet=snippet):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location, snippet),
                "link": link,
                "source": "NTU Careers",
            }
        )

    return jobs


def fetch_remoterocketship_jobs():
    """
    RemoteRocketship: AI researcher / AI research scientist 远程岗位。
    """
    urls = [
        "https://www.remoterocketship.com/jobs/ai-researcher/",
        "https://www.remoterocketship.com/jobs/ai-research-scientist/",
    ]

    jobs = []

    for url in urls:
        resp = safe_get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for apply_link in soup.find_all("a", string=lambda s: s and "Apply" in s):
            card = apply_link.find_parent("div")
            if not card:
                continue

            text = card.get_text(" ", strip=True)

            title_tag = card.find(["h3", "h2", "strong"])
            title = title_tag.get_text(strip=True) if title_tag else "AI role"

            company_tag = card.find("h4")
            company = company_tag.get_text(strip=True) if company_tag else "Remote company"

            location = ""
            for part in text.split("  "):
                if "Remote" in part:
                    location = part.strip()
                    break
            if not location:
                location = "Remote"

            if not is_relevant_job(title, company, location, snippet=text):
                continue

            if any(k in text.lower() for k in EXCLUDE_COMPANY_KEYWORDS):
                continue

            link = apply_link.get("href")
            if link and link.startswith("/"):
                link = urljoin("https://www.remoterocketship.com", link)

            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "location": location,
                    "remote": True,
                    "link": link or url,
                    "source": "RemoteRocketship",
                }
            )

    return jobs


def fetch_mbzuai_jobs():
    url = "https://mbzuai.ac.ae/careers/"
    resp = safe_get(url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []
    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        if not title:
            continue
        low = title.lower()

        if not any(
            k in low for k in ["research", "engineer", "scientist", "ai", "machine", "assistant"]
        ):
            continue

        link = urljoin(url, a["href"])
        company = "MBZUAI"
        location = "Abu Dhabi"
        snippet = title

        if not is_relevant_job(title, company, location, snippet):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location, snippet),
                "link": link,
                "source": "MBZUAI",
            }
        )
    return jobs


def fetch_ethz_jobs():
    """
    ETH Zürich – 官方 jobs.ethz.ch
    实际职位链接是 /job/view/xxx，不是 /vacancies/
    """
    url = "https://jobs.ethz.ch"
    resp = safe_get(url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []
    # 关键：匹配 '/job/view/' 而不是 '/vacancies/'
    for a in soup.select("a[href*='/job/view/']"):
        title = a.get_text(strip=True)
        if not title:
            continue
        low = title.lower()
        if not any(k in low for k in ["research", "engineer", "scientist", "machine", "ai", "deep"]):
            continue

        link = urljoin(url, a["href"])
        company = "ETH Zürich"
        location = "Switzerland"
        snippet = title

        if not is_relevant_job(title, company, location, snippet):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "ETH",
            }
        )
    return jobs


def fetch_epfl_jobs():
    """
    EPFL – Careers 门户有 cookie/JS，简单 HTML 抓不到时就返回空。
    这里保留函数，但很可能是 0 jobs。
    """
    url = "https://careers.epfl.ch/job-search/?keyword=research"
    resp = safe_get(url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []
    # 简单兜底：尽量匹配包含 research/ai/ml 的链接
    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        if not title:
            continue
        low = title.lower()
        if not any(k in low for k in ["research", "engineer", "ml", "ai", "deep"]):
            continue
        link = urljoin(url, a["href"])
        company = "EPFL"
        location = "Switzerland"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": False,
                "link": link,
                "source": "EPFL",
            }
        )
    return jobs


def fetch_tno_jobs():
    url = "https://www.tno.nl/en/career/vacancies/?q=machine%20learning"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for item in soup.select("a[href*='/en/career/vacancies/']"):
        title = item.get_text(strip=True)
        if not title:
            continue

        low = title.lower()

        if not any(k in low for k in ["research", "machine", "ai", "ml", "engineer", "data", "scientist"]):
            continue

        link = urljoin(url, item["href"])
        company = "TNO"
        location = "Netherlands"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "TNO",
            }
        )

    return jobs


BASE_URL = "https://jobs.fraunhofer.de"
SEARCH_URL = BASE_URL + "/search/"

FRAUNHOFER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}

fraunhofer_session = requests.Session()
fraunhofer_session.headers.update(FRAUNHOFER_HEADERS)


def fetch_fraunhofer_jobs():
    """
    抓 https://jobs.fraunhofer.de/search/?q=ai&startrow=0,25,50... 上的所有 /job/ 链接，
    再用你自己的 is_relevant_job() 过滤。
    """
    all_jobs = []
    startrow = 0
    page_size = 25  # 页面上写了 “Ergebnisse 1 – 25 von ...”

    while True:
        params = {
            "q": "ai",
            "startrow": startrow,
        }
        print(f"[fraunhofer] startrow={startrow}")
        resp = fraunhofer_session.get(SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. 抓所有 /job/ 链接
        links = soup.select("a[href*='/job/']")
        if not links:
            # 没职位了，或者被 cookie 页挡住
            break

        new_count = 0

        for a in links:
            href = a.get("href")
            title = a.get_text(strip=True)

            if not href or not title:
                continue

            link = urljoin(BASE_URL, href)
            company = "Fraunhofer"
            location = "Germany"  # 先简单写死

            # 这里用你原来的过滤逻辑
            if not is_relevant_job(title, company, location, snippet=title):
                continue

            all_jobs.append(
                {
                    "company": company,
                    "title": title,
                    "location": location,
                    "remote": detect_remote(location, title),
                    "link": link,
                    "source": "Fraunhofer",
                }
            )
            new_count += 1

        print(f"[fraunhofer] 这一页符合条件的职位: {new_count}")

        # 分页：如果这一页的 job 链接不到 page_size 个，说明已经到最后一页
        if len(links) < page_size:
            break

        startrow += page_size

    return all_jobs


def fetch_sintef_jobs():
    """
    SINTEF – Vacant positions 页面，实际职位链接跳到 delta.hr-manager.net。
    """
    url = "https://www.sintef.no/en/sintef-group/career/vacant-positions/"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # 关键：链接域名是 delta.hr-manager.net
    for a in soup.select("a[href*='delta.hr-manager.net']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        low = title.lower()
        # 排除“更新申请”等文字，尽量要真正职位
        if "update previous applications" in low:
            continue

        if not any(k in low for k in ["research", "engineer", "scientist", "ai", "ml", "deep", "data", "robot"]):
            continue

        link = a.get("href")
        if link and link.startswith("/"):
            link = urljoin(url, link)

        company = "SINTEF"
        location = "Norway"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "SINTEF",
            }
        )

    return jobs


def fetch_vtt_jobs():
    """
    VTT (Finland) – 重点抓 AI / ML / Robotics / Simulation 相关岗位
    """
    url = "https://www.vttresearch.com/en/working-vtt"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/en/careers/open-positions/']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "VTT"
        location = "Finland"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "VTT",
            }
        )

    return jobs


def fetch_tudelft_jobs():
    """
    TU Delft – 抓 Research / Engineer / AI / Robotics 相关岗位
    """
    url = "https://www.tudelft.nl/en/about-tu-delft/working-at-tu-delft/search-jobs"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/vacature'], a[href*='/job']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "TU Delft"
        location = "Netherlands"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "TU Delft",
            }
        )

    return jobs


def fetch_kth_jobs():
    """
    KTH (Sweden) – 抓 AI / ML / Robotics / Control 相关岗位
    """
    url = "https://www.kth.se/lediga-jobb"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/jobb'], a[href*='/positions']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "KTH"
        location = "Sweden"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "KTH",
            }
        )

    return jobs


def fetch_dtu_jobs():
    """
    DTU (Denmark) – 抓 AI / Robotics / Automation / Control 岗位
    """
    url = "https://www.dtu.dk/english/About/JOB-and-CAREER/vacant-positions"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/About/JOB-and-CAREER/vacant-positions']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "DTU"
        location = "Denmark"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": detect_remote(location),
                "link": link,
                "source": "DTU",
            }
        )

    return jobs


def fetch_stability_jobs():
    """
    Stability AI Careers – 抓 Research / Scientist / Engineer 中和生成式相关的岗位
    """
    url = "https://stability.ai/careers"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/careers/']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "Stability AI"
        location = "Europe / Remote"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": True,
                "link": link,
                "source": "Stability",
            }
        )

    return jobs


def fetch_runway_jobs():
    """
    Runway Careers – 抓 research / generative / video / ml 相关岗位
    """
    url = "https://runwayml.com/careers"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/careers/']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "Runway"
        location = "Europe / Remote"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": True,
                "link": link,
                "source": "Runway",
            }
        )

    return jobs


def fetch_eleven_jobs():
    """
    ElevenLabs Careers – 抓 research / ml / generative / audio-multimodal 岗位
    """
    url = "https://elevenlabs.io/careers"
    resp = safe_get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    for a in soup.select("a[href*='/careers/']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        link = urljoin(url, a.get("href"))
        company = "ElevenLabs"
        location = "Europe / Remote"

        if not is_relevant_job(title, company, location):
            continue

        jobs.append(
            {
                "company": company,
                "title": title,
                "location": location,
                "remote": True,
                "link": link,
                "source": "ElevenLabs",
            }
        )

    return jobs
def fetch_jobscentral_jobs():
    """
    JobsCentral 新加坡岗位（jobscentral.com.sg）
    通过 ?title= 查询若干 AI/ML 相关关键词，再逐个进详情页过滤。
    """
    base_list_url = "https://jobscentral.com.sg/jobs"
    base_domain = "https://jobscentral.com.sg"
    search_terms = [
        "research engineer",
        "research scientist",
        "machine learning",
        "deep learning",
        "ai engineer",
        "ml engineer",
        "data scientist",
        "computer vision",
        "nlp",
        "generative",
    ]

    jobs = []
    seen_links = set()

    for term in search_terms:
        query = term.replace(" ", "+")
        list_url = f"{base_list_url}?title={query}&location=Singapore"
        resp = safe_get(list_url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # JobsCentral 职位详情链接形如 /jobs/other-jobs/1035726
        for a in soup.select("a[href*='/jobs/']"):
            href = a.get("href")
            if not href:
                continue

            # 排除顶部 “Browse jobs” 这种短链接（例如 "/jobs"）
            if href.count("/") <= 2:
                continue

            link = urljoin(base_domain, href)

            # 避免重复
            if link in seen_links:
                continue
            seen_links.add(link)

            # 进入详情页，拿更多文本用于过滤
            detail_resp = safe_get(link)
            if not detail_resp:
                continue

            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

            # 标题：优先用 <h1>，退化到 <title> 或列表页上的文本
            title_tag = detail_soup.find("h1") or detail_soup.find("h2")
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                # 兜底：用详情页 title 标签或列表页 a 文本
                if detail_soup.title:
                    title = detail_soup.title.get_text(strip=True)
                else:
                    title = a.get_text(strip=True)

            # 位置：JobsCentral 大部分都是新加坡岗位
            location = "Singapore"

            # snippet：整个页面文本，方便关键词过滤
            snippet = detail_soup.get_text(" ", strip=True)

            # 这里只能粗略给个 company，真正公司名结构比较散，就先不强行解析
            company = "JobsCentral listing"

            if not is_relevant_job(title, company, location, snippet=snippet):
                continue

            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "location": location,
                    "remote": detect_remote(location, snippet),
                    "link": link,
                    "source": "JobsCentral",
                }
            )

    return jobs
def fetch_mycareersfuture_jobs():
    """
    MyCareersFuture (CareersFuture Job Portal):
    遍历多种 AI/ML 关键词，按新发职位排序。
    """
    base_url = "https://www.mycareersfuture.gov.sg/search"
    query_terms = [
        "research engineer",
        "research scientist",
        "machine learning",
        "deep learning",
        "ai engineer",
        "ml engineer",
        "data scientist",
        "nlp",
        "computer vision",
        "generative",
    ]

    jobs = []
    seen_links = set()

    for term in query_terms:
        search_param = term.replace(" ", "%20")
        url = f"{base_url}?search={search_param}&sortBy=new_posting_date"
        resp = safe_get(url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for card in soup.select("a[data-testid='job-card-link']"):
            title = card.get_text(strip=True)
            link = urljoin("https://www.mycareersfuture.gov.sg", card["href"])

            if link in seen_links:
                continue
            seen_links.add(link)

            parent = card.find_parent("div") or card
            company_tag = parent.select_one("[data-testid='company-hire-info']")
            location_tag = parent.select_one("[data-testid='job-location']")

            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            location = location_tag.get_text(strip=True) if location_tag else "Singapore"

            snippet = parent.get_text(" ", strip=True)

            if not is_relevant_job(title, company, location, snippet=snippet):
                continue

            jobs.append(
                {
                    "company": company,
                    "title": title,
                    "location": location,
                    "remote": detect_remote(location, snippet),
                    "link": link,
                    "source": "MyCareersFuture",
                }
            )

    return jobs


# ========= 汇总 & 打印 =========


def collect_all_jobs():
    all_jobs = []

    fetchers = [
        # 🇪🇺 核心欧洲科研
        fetch_tno_jobs,
        fetch_fraunhofer_jobs,
        fetch_sintef_jobs,
        fetch_ethz_jobs,
        fetch_epfl_jobs,
        fetch_vtt_jobs,
        fetch_tudelft_jobs,
        fetch_kth_jobs,
        fetch_dtu_jobs,
        # 🌍 前沿生成式 AI，不是美企
        fetch_mistral_jobs,
        fetch_stability_jobs,
        fetch_runway_jobs,
        fetch_eleven_jobs,
        # 🇸🇬 新加坡科研
        fetch_aisingapore_jobs,
        fetch_astar_jobs,
        fetch_nus_jobs,
        fetch_ntu_jobs,
        fetch_sit_jobs,
        fetch_mycareersfuture_jobs,  # CareersFuture job portal
        fetch_jobscentral_jobs,      # JobsCentral 新增
        # Remote 欧洲岗 / 海外科研
        # Remote 欧洲岗
        fetch_remoterocketship_jobs,
        fetch_mbzuai_jobs,
    ]

    for f in fetchers:
        print(f"[INFO] Fetching from {f.__name__} ...")
        try:
            jobs = f()
            print(f"[INFO]   -> {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:  # pragma: no cover - 网络异常
            print(f"[ERROR] {f.__name__} 发生异常: {e}")

    # 按链接去重
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = j["link"]
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    return unique_jobs


def score_job(job):
    score = 0

    title = job.get("title", "").lower()
    snippet = job.get("snippet", "").lower()
    company = job.get("company", "").lower()
    location = job.get("location", "").lower()

    # ===== 你核心能力（高权重） =====
    high = [
        ("multimodal", 10),
        ("multi-modal", 10),
        ("large language model", 9),
        ("foundation", 8),
        ("agent", 8),
        ("rlhf", 8),
        ("reinforcement", 8),
        ("generative", 8),
        ("diffusion", 7),
        ("vae", 6),
        ("vq", 6),
        ("token", 6),
        ("tokenization", 6),
        ("motion", 6),
        ("bvh", 5),
        ("3d", 5),
    ]
    for kw, weight in high:
        if kw in title or kw in snippet:
            score += weight

    # ===== robotics / control =====
    robotics = [
        ("robot", 6),
        ("embodied", 6),
        ("simulation", 5),
        ("control", 5),
        ("autonomous", 4),
    ]
    for kw, weight in robotics:
        if kw in title or kw in snippet:
            score += weight

    # ===== research engineer系 =====
    if "research engineer" in title:
        score += 10
    if "research scientist" in title:
        score += 8
    if "applied scientist" in title:
        score += 8

    # generic engineer 加一点
    if "engineer" in title:
        score += 3

    # ===== 地理偏好 =====
    if "remote" in location:
        score += 10
    if any(k in location for k in ["netherlands", "norway", "finland", "sweden", "germany", "switzerland"]):
        score += 7
    if "singapore" in location:
        score += 5
    if "us" in location:
        score -= 1

    # ===== 研究机构偏好 =====
    preferred = {
        "tno": 8,
        "fraunhofer": 7,
        "sintef": 7,
        "eth": 7,
        "epfl": 6,
        "mistral": 9,
        "runway": 8,
        "stability": 8,
        "deepmind": 7,
        "microsoft research": 6,
        "aisingapore": 5,
        "astar": 5,
    }
    for keyword, weight in preferred.items():
        if keyword in company:
            score += weight

    # ===== 黑名单 =====
    blacklist = ["huawei", "alibaba", "tencent", "bytedance", "sensetime"]
    if any(k in company for k in blacklist):
        return -100

    return score


def print_jobs(jobs):
    if not jobs:
        print("今天没有抓到符合条件的职位。")
        return

    for i, job in enumerate(jobs, 1):
        remote_flag = " 🌍REMOTE" if job.get("remote") else ""
        print(f"#{i} {job['company']} — {job['title']}{remote_flag}")
        print(f"   ⭐ Score: {job.get('score', 0)}")
        print(f"   📍 {job['location']} | 来源: {job['source']}")
        print(f"   🔗 {job['link']}")
        print("-" * 60)


def main():
    print("开始抓取职位...\n")
    jobs = collect_all_jobs()
    for job in jobs:
        job["score"] = score_job(job)
    sorted_jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)
    print_jobs(sorted_jobs)
    return sorted_jobs


if __name__ == "__main__":
    main()
