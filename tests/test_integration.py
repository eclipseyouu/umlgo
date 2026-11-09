import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from src.activity_diagram import ActivityDiagram
from src.json_parser import parse_json
from src.main import main
from src.markdown_writer import write_activity_report, write_sequence_report
from src.plugin_loader import PluginManager
from src.sequence_diagram import SequenceDiagram

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


class IntegrationTest(unittest.TestCase):
    def test_sequence_render(self):
        data = parse_json((SAMPLES / "sequence_sample.json").read_text(encoding="utf-8"))
        diagram = SequenceDiagram.from_data(data)
        expected = (
            "Sequence Diagram:\n"
            "Customer -> OrderSystem: PlaceOrder(item: Milk, quantity: 2)\n"
            "OrderSystem -> Order: CreateOrder(id: 123, items: [Milk])\n"
            "Order -> PaymentGateway: ProcessPayment(amount: 50)"
        )
        self.assertEqual(diagram.render(), expected)
        self.assertEqual(
            diagram.participants(),
            ["Customer", "OrderSystem", "Order", "PaymentGateway"],
        )

    def test_activity_render_and_analysis(self):
        data = parse_json((SAMPLES / "activity_sample.json").read_text(encoding="utf-8"))
        diagram = ActivityDiagram.from_data(data)
        expected = (
            "Activity Diagram:\n"
            "StartOrderProcessing -> CheckInventory\n"
            "CheckInventory -> ProcessPayment (if inventoryAvailable AND NOT blacklisted)\n"
            "CheckInventory -> NotifyCustomer (if NOT (inventoryAvailable AND NOT blacklisted))\n"
            "ProcessPayment -> CompleteOrder\n"
            "NotifyCustomer -> EndOrderProcessing"
        )
        self.assertEqual(diagram.render(), expected)

        analysis = diagram.analyze()
        self.assertEqual(analysis["roots"], ["StartOrderProcessing"])
        self.assertEqual(analysis["unreachable"], [])
        self.assertEqual(analysis["cycles"], [])
        self.assertFalse(analysis["has_cycle"])
        self.assertEqual(analysis["dead_ends"], ["CompleteOrder"])
        self.assertEqual(
            analysis["topological_order"],
            [
                "StartOrderProcessing",
                "CheckInventory",
                "ProcessPayment",
                "NotifyCustomer",
                "CompleteOrder",
                "EndOrderProcessing",
            ],
        )

    def test_markdown_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            sequence_data = parse_json(
                (SAMPLES / "sequence_sample.json").read_text(encoding="utf-8")
            )
            activity_data = parse_json(
                (SAMPLES / "activity_sample.json").read_text(encoding="utf-8")
            )
            sequence = SequenceDiagram.from_data(sequence_data)
            activity = ActivityDiagram.from_data(activity_data)

            sequence_path = write_sequence_report(directory / "sequence-diagram.md", sequence)
            activity_path = write_activity_report(directory / "activity-diagram.md", activity)

            sequence_text = sequence_path.read_text(encoding="utf-8")
            activity_text = activity_path.read_text(encoding="utf-8")
            self.assertIn("# Диаграмма последовательности", sequence_text)
            self.assertIn("PaymentGateway", sequence_text)
            self.assertIn("## Анализ", activity_text)
            self.assertIn("Циклы", activity_text)
            self.assertIn("не найдены", activity_text)
            self.assertIn("Порядок выполнения", activity_text)

    def test_mermaid_plugin(self):
        manager = PluginManager()
        manager.load_directory(ROOT / "plugins")
        self.assertTrue(manager.plugins[0]["loaded"])
        exporter = manager.registry["exporters"]["mermaid"]

        activity_data = parse_json(
            (SAMPLES / "activity_sample.json").read_text(encoding="utf-8")
        )
        activity = ActivityDiagram.from_data(activity_data)
        text = exporter(activity, "activity")
        self.assertIn("flowchart TD", text)
        self.assertIn("inventoryAvailable AND NOT blacklisted", text)

        sequence_data = parse_json(
            (SAMPLES / "sequence_sample.json").read_text(encoding="utf-8")
        )
        sequence = SequenceDiagram.from_data(sequence_data)
        text = exporter(sequence, "sequence")
        self.assertIn("sequenceDiagram", text)
        self.assertIn("PlaceOrder", text)

    def test_cli_render(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--file",
                    str(SAMPLES / "activity_sample.json"),
                    "--render",
                    "activity",
                ]
            )
        self.assertEqual(code, 0)
        self.assertIn("Activity Diagram:", output.getvalue())
        self.assertIn("CheckInventory -> ProcessPayment", output.getvalue())


if __name__ == "__main__":
    unittest.main()
