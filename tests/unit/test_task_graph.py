"""Unit tests for TaskGraph."""

from core.planner.task_graph import NodeStatus, PlanNode, TaskGraph


class TestTaskGraph:
    def _graph(self) -> TaskGraph:
        g = TaskGraph(goal="test")
        g.add_node(PlanNode(node_id="a", description="step a"))
        g.add_node(PlanNode(node_id="b", description="step b", depends_on=["a"]))
        g.add_node(PlanNode(node_id="c", description="step c", depends_on=["a"]))
        return g

    def test_ready_nodes_returns_roots(self):
        g = self._graph()
        ready = g.ready_nodes()
        assert len(ready) == 1
        assert ready[0].node_id == "a"

    def test_ready_after_completing_dependency(self):
        g = self._graph()
        g.nodes[0].status = NodeStatus.DONE
        ready_ids = {n.node_id for n in g.ready_nodes()}
        assert ready_ids == {"b", "c"}

    def test_is_complete_when_all_done(self):
        g = self._graph()
        assert not g.is_complete()
        for n in g.nodes:
            n.status = NodeStatus.DONE
        assert g.is_complete()

    def test_has_failures(self):
        g = self._graph()
        g.nodes[0].status = NodeStatus.FAILED
        assert g.has_failures()
