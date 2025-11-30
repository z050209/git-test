python open_url.py -f ./results/job_results_20251129_150143.json
python open_url.py -k "Research Engineer" -f ./results/job_results_20251129_150143.json

python open_url.py -r 50 60 -f ./results/job_results_20251129_150143.json

python fetch_papers.py --from-date 2025-06-01 --max-papers 5
python fetch_papers.py --max-papers 5

python fetch_papers.py `
  --people-json data\stanford_people.json `
  --out-json results\stanford_ai_papers_2025.json

python build_jobs_dashboard.py --in-json results\job_results_20251129_150143.json

python build_html_dashboard.py --in-json results/stanford_ai_papers_openalex_20251130_085700.json
python build_html_dashboard.py --in-json results\stanford_ai_papers_openalex_20251130_115546.json


