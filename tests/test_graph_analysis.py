import unittest

from src.graph_analysis import analyze_graph, format_analysis


class GraphAnalysisTest(unittest.TestCase):
    def test_acyclic_graph(self):
        result = analyze_graph(
            ["Start", "Middle", "End"],
            [("Start", "Middle"), ("Middle", "End")],
        )
        self.assertFalse(result["has_cycle"])
        self.assertEqual(result["topological_order"], ["Start", "Middle", "End"])
        self.assertEqual(result["unreachable"], [])
        self.assertEqual(result["sinks"], ["End"])
        self.assertEqual(result["dead_ends"], [])

    def test_simple_cycle(self):
        result = analyze_graph(["A", "B"], [("A", "B"), ("B", "A")])
        self.assertTrue(result["has_cycle"])
        self.assertEqual(result["cycles"], [["A", "B"]])
        self.assertIsNone(result["topological_order"])

    def test_self_loop(self):
        result = analyze_graph(["A", "End"], [("A", "A"), ("A", "End")])
        self.assertTrue(result["has_cycle"])
        self.assertEqual(result["cycles"], [["A"]])

    def test_multiple_cycles(self):
        result = analyze_graph(
            ["Start", "A", "B", "C", "D", "End"],
            [
                ("Start", "A"),
                ("A", "B"),
                ("B", "A"),
                ("Start", "C"),
                ("C", "D"),
                ("D", "C"),
                ("A", "End"),
            ],
        )
        self.assertEqual(len(result["cycles"]), 2)
        self.assertEqual(result["cycles"], [["A", "B"], ["C", "D"]])

    def test_unreachable_component(self):
        result = analyze_graph(
            ["Start", "Next", "C", "D"],
            [
                ("Start", "Next"),
                ("C", "D"),
                ("D", "C"),
            ],
        )
        self.assertEqual(result["unreachable"], ["C", "D"])
        self.assertEqual(result["roots"], ["Start"])
        self.assertTrue(result["has_cycle"])

    def test_multiple_roots_warning(self):
        result = analyze_graph(["A", "B"], [])
        self.assertEqual(result["roots"], ["A", "B"])
        self.assertTrue(
            any("Multiple start nodes" in warning for warning in result["warnings"])
        )

    def test_dead_end(self):
        result = analyze_graph(
            ["Start", "Middle", "End"],
            [("Start", "Middle"), ("Middle", "End")],
        )
        self.assertEqual(result["dead_ends"], [])
        result = analyze_graph(["Start", "Middle"], [("Start", "Middle")])
        self.assertEqual(result["dead_ends"], ["Middle"])
        self.assertTrue(any("Dead-end" in warning for warning in result["warnings"]))

    def test_duplicate_edges_are_ignored(self):
        result = analyze_graph(
            ["A", "End"],
            [("A", "End"), ("A", "End"), ("A", "End")],
        )
        self.assertEqual(result["edge_count"], 1)
        self.assertEqual(result["topological_order"], ["A", "End"])

    def test_empty_graph(self):
        result = analyze_graph([], [])
        self.assertEqual(result["nodes"], [])
        self.assertFalse(result["has_cycle"])

    def test_unknown_node(self):
        with self.assertRaises(ValueError):
            analyze_graph(["A"], [("A", "B")])

    def test_format_analysis(self):
        result = analyze_graph(["A", "End"], [("A", "End")])
        text = format_analysis(result)
        self.assertIn("Анализ графа деятельности", text)
        self.assertIn("Циклы: не найдены", text)


if __name__ == "__main__":
    unittest.main()
