import os
import unittest

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover - environment without deps
    BeautifulSoup = None

import stanford_research_agent as agent

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class StanfordResearchAgentTests(unittest.TestCase):
    def read_fixture(self, name: str) -> str:
        with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as f:
            return f.read()

    def test_summarize_text_limits_sentences_and_length(self):
        text = (
            "Sentence one about RLHF. Sentence two about tokenization and multimodal models. "
            "Sentence three should be truncated."
        )
        summary = agent.summarize_text(text, max_sentences=2, max_length=120)
        self.assertIn("RLHF", summary)
        self.assertIn("tokenization", summary)
        self.assertNotIn("Sentence three", summary)
        self.assertLessEqual(len(summary), 120)

    @unittest.skipIf(BeautifulSoup is None, "beautifulsoup4 is not installed")
    def test_extract_key_diagram_prefers_meta(self):
        html = self.read_fixture("person_publications.html")
        soup = BeautifulSoup(html, "lxml")
        diagram = agent.extract_key_diagram_url(soup, "https://example.com/profile")
        self.assertEqual(diagram, "https://example.com/images/figure1.png")

    @unittest.skipIf(BeautifulSoup is None, "beautifulsoup4 is not installed")
    def test_extract_people_and_papers(self):
        lab_html = self.read_fixture("lab_people.html")
        people = agent.extract_people_from_html(lab_html, "https://lab.stanford.edu/people")
        self.assertGreaterEqual(len(people), 2)
        self.assertEqual(people[0].role, "Professor")

        papers_html = self.read_fixture("person_publications.html")
        papers = agent.extract_publications_from_html(papers_html, "https://lab.stanford.edu/people/alice")
        self.assertEqual(len(papers), 2)
        titles = [p.title for p in papers]
        self.assertIn("Robust Multimodal Diffusion Models", titles)
        self.assertTrue(all(p.overview for p in papers))

    def test_build_html_page_includes_people(self):
        papers = [
            agent.Paper(
                title="Sample Paper",
                link="https://example.com/paper",
                overview="A short overview.",
                key_diagram="https://example.com/fig.png",
            )
        ]
        person = agent.Person(
            name="Test Person", role="Researcher", homepage="https://example.com", papers=papers
        )
        lab = agent.Lab(name="Test Lab", url="https://example.com/lab", topics=["llm"], people=[person])
        html = agent.build_html_page([lab])
        self.assertIn("Test Lab", html)
        self.assertIn("Sample Paper", html)
        self.assertIn("fig.png", html)


if __name__ == "__main__":
    unittest.main()
