python open_url.py -f ./results/job_results_20251129_150143.json
python open_url.py -k "Research Engineer" -f ./results/job_results_20251129_150143.json

python open_url.py -r 50 60 -f ./results/job_results_20251129_150143.json

python fetch_papers.py --from-date 2025-06-01
python fetch_papers.py --max-papers 5

python fetch_papers.py `
  --people-json data\stanford_people.json `
  --out-json results\stanford_ai_papers_2025.json

python fetch_papers.py --from-date 2025-06-01 
python build_html_dashboard.py --in-json results/stanford_ai_papers_openalex_20251130_085700.json
python build_jobs_dashboard.py --in-json result/job_results_20251129_150143.json


git fetch origin
git checkout data-history
git branch
ls results
rm results/job_results_20251130_012121.html
rm results/job_results_20251130_020737.html
rm results/stanford_ai_papers_openalex_20251129_123000.html
git add results
git commit -m "cleanup old dashboards"
git push origin data-history


