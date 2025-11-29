# from job_search import collect_all_jobs, score_job
# from email_client import SMTPConfig, send_job_results

# jobs = collect_all_jobs()
# for job in jobs:
#     job["score"] = score_job(job)

# sorted_jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)
# config = SMTPConfig.from_env()
# send_job_results(sorted_jobs, "z050209@gmail.com", config)

from job_search import collect_all_jobs, score_job
import json
from datetime import datetime

def save_job_results(jobs, path: str) -> None:
    """把 job 列表保存成 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def main():
    # 1. 抓取职位
    jobs = collect_all_jobs()

    # 2. 打分
    for job in jobs:
        job["score"] = score_job(job)

    # 3. 排序
    sorted_jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)

    # 4. 保存文件
    filename = f"job_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_job_results(sorted_jobs, filename)

    print(f"✅ 已保存到 {filename}")


if __name__ == "__main__":
    main()
