"""sim_user.render_template: fixed and dynamic ("missing") placeholders."""
import unittest

from harness.users.sim_user import render_template

PAPERS = {"W1": {"title": "Alpha"}, "W2": {"title": "Beta"}, "10.1101/2021.01.05.21249310": {"title": "Gamma"}}


class TestRenderTemplate(unittest.TestCase):
    def test_fixed(self):
        self.assertEqual(render_template('Why not "{title:W1}" ({id:W2})?', PAPERS),
                         ('Why not "Alpha" (W2)?', ["W1", "W2"]))

    def test_missing_picks_first_uncited(self):
        msg, t = render_template('Why not "{title:missing:W1,W2}"?', PAPERS, cited={"W1"})
        self.assertEqual((msg, t), ('Why not "Beta"?', ["W2"]))

    def test_missing_falls_back_to_first_when_all_cited(self):
        self.assertEqual(render_template("{id:missing:W1,W2}", PAPERS, cited={"W1", "W2"}), ("W1", ["W1"]))

    def test_missing_respects_report_of(self):
        from harness.users.sim_user import SimUser
        class Rec:
            def __init__(self): self.events = []
            def event(self, t, **d): self.events.append((t, d))
        case = {"goal": "g", "initial_prompt": "hi", "report_of": {"W2": "W1"},
                "script": {"followups": [{"after_turn": 1, "message": "{id:missing:W1,10.1101/2021.01.05.21249310}"}]}}
        u = SimUser(case, "p", PAPERS, "m", Rec(), 6, find_ids=lambda t: [i for i in PAPERS if i in t])
        u.client = None
        u.next_message(None)
        msg = u.next_message("Included: W2 (a preprint of the W1 trial).")
        self.assertEqual(msg, "10.1101/2021.01.05.21249310")   # W1 counts as cited through its report W2

    def test_doi_style_id(self):
        self.assertEqual(render_template("{title:10.1101/2021.01.05.21249310}", PAPERS)[0], "Gamma")

    def test_unknown_ids_raise(self):
        with self.assertRaises(KeyError):
            render_template("{title:W9}", PAPERS)
        with self.assertRaises(KeyError):
            render_template("{title:missing:W1,W9}", PAPERS)


if __name__ == "__main__":
    unittest.main()
