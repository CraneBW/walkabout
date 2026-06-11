"""Tests for RendererRegistry and custom_render in walkabout.core.execute_util."""
import pytest
from walkabout.core.execute_util import (
    RendererRegistry,
    custom_render,
    Rendering,
    _current_renderings,
    pop_renderings,
)


@pytest.fixture(autouse=True)
def clear_renderings():
    """Clear accumulated renderings before and after each test."""
    pop_renderings()
    yield
    pop_renderings()


class TestRendererRegistry:
    """Unit tests for the RendererRegistry class."""

    def test_register_stores_function(self):
        registry = RendererRegistry()

        def render_fn(data, style):
            return f"rendered: {data}"

        registry.register("vega", render_fn)
        assert registry.get("vega") is render_fn

    def test_get_returns_correct_function(self):
        registry = RendererRegistry()

        def fn_a(data, style):
            return f"a: {data}"

        def fn_b(data, style):
            return f"b: {data}"

        registry.register("type_a", fn_a)
        registry.register("type_b", fn_b)
        assert registry.get("type_a") is fn_a
        assert registry.get("type_b") is fn_b

    def test_register_existing_type_raises(self):
        registry = RendererRegistry()

        def fn_a(data, style):
            pass

        registry.register("my_type", fn_a)

        def fn_b(data, style):
            pass

        with pytest.raises(ValueError, match="already registered"):
            registry.register("my_type", fn_b)

    def test_has_returns_true_for_registered(self):
        registry = RendererRegistry()

        def fn(data, style):
            pass

        registry.register("exists", fn)
        assert registry.has("exists") is True

    def test_has_returns_false_for_unregistered(self):
        registry = RendererRegistry()
        assert registry.has("nonexistent") is False

    def test_list_returns_all_type_names(self):
        registry = RendererRegistry()

        def fn(data, style):
            pass

        registry.register("a", fn)
        registry.register("b", fn)
        registry.register("c", fn)

        names = registry.list()
        assert sorted(names) == ["a", "b", "c"]

    def test_all_returns_full_dict(self):
        registry = RendererRegistry()

        def fn_a(data, style):
            pass

        def fn_b(data, style):
            pass

        registry.register("x", fn_a)
        registry.register("y", fn_b)

        all_reg = registry.all()
        assert all_reg["x"] is fn_a
        assert all_reg["y"] is fn_b
        assert len(all_reg) == 2

    def test_empty_registry_lists_are_empty(self):
        registry = RendererRegistry()
        assert registry.list() == []
        assert registry.all() == {}
        assert registry.has("anything") is False
        assert registry.get("anything") is None

    def test_register_multiple_types(self):
        """Register 3 different types and verify all are retrievable."""
        registry = RendererRegistry()

        def fn_a(data, style):
            return f"a: {data}"

        def fn_b(data, style):
            return f"b: {data}"

        def fn_c(data, style):
            return f"c: {data}"

        registry.register("type_a", fn_a)
        registry.register("type_b", fn_b)
        registry.register("type_c", fn_c)

        assert registry.get("type_a") is fn_a
        assert registry.get("type_b") is fn_b
        assert registry.get("type_c") is fn_c
        assert sorted(registry.list()) == ["type_a", "type_b", "type_c"]
        assert len(registry.all()) == 3

    def test_get_unknown_type_returns_none(self):
        """get() for a nonexistent type returns None."""
        registry = RendererRegistry()
        assert registry.get("nonexistent") is None


class TestCustomRender:
    """Unit tests for the custom_render() function."""

    def test_custom_render_with_registered_type(self):
        registry = RendererRegistry()

        def vega_fn(data, style):
            return {"svg": data}

        registry.register("vega", vega_fn)
        from walkabout.core.execute_util import set_renderer_registry

        set_renderer_registry(registry)
        try:
            custom_render("vega", data='{"x": 1}')
            renderings = pop_renderings()
            assert len(renderings) == 1
            assert renderings[0].type == "vega"
            assert renderings[0].data == '{"x": 1}'
        finally:
            set_renderer_registry(None)

    def test_custom_render_unknown_type_strict_false(self):
        custom_render("unknown_chart", data="some data", strict=False)
        renderings = pop_renderings()
        assert len(renderings) == 1
        assert renderings[0].type == "unknown_chart"
        assert renderings[0].data == "some data"

    def test_custom_render_unknown_type_strict_true_raises(self):
        with pytest.raises(ValueError, match="not registered"):
            custom_render("nonexistent", data="x", strict=True)

    def test_custom_render_no_style_defaults_to_none(self):
        custom_render("foo", data="bar")
        renderings = pop_renderings()
        assert renderings[0].style is None

    def test_custom_render_with_style(self):
        custom_render("chart", data="data", style={"width": "100%"})
        renderings = pop_renderings()
        assert renderings[0].style == {"width": "100%"}

    def test_multiple_renderings_in_same_step(self):
        from walkabout.core.execute_util import text

        custom_render("type_a", data="first")
        text("hello")
        custom_render("type_b", data="second")
        renderings = pop_renderings()
        assert len(renderings) == 3
        assert renderings[0].type == "type_a"
        assert renderings[1].type == "markdown"
        assert renderings[1].data == "hello"
        assert renderings[2].type == "type_b"

    def test_custom_render_with_all_parameters(self):
        """custom_render() accepts type, data, style, and strict=False."""
        custom_render("some_type", data="hello", style={"color": "red"}, strict=False)
        renderings = pop_renderings()
        assert len(renderings) == 1
        assert renderings[0].type == "some_type"
        assert renderings[0].data == "hello"
        assert renderings[0].style == {"color": "red"}

    def test_custom_render_appends_to_current_renderings(self):
        """After custom_render(), pop_renderings() should include the new Rendering."""
        # Clear any accumulated renderings first
        initial = pop_renderings()
        assert len(initial) == 0

        custom_render("chart", data="viz-data")
        renderings = pop_renderings()
        assert len(renderings) == 1
        assert renderings[0].type == "chart"
        assert renderings[0].data == "viz-data"


class TestRegistrySingleton:
    """Tests for the module-level registry singleton."""

    def test_get_renderer_registry_creates_singleton(self):
        from walkabout.core.execute_util import (
            get_renderer_registry,
            _renderer_registry,
            set_renderer_registry,
        )

        # Reset first
        set_renderer_registry(None)
        reg1 = get_renderer_registry()
        reg2 = get_renderer_registry()
        assert reg1 is reg2

    def test_set_renderer_registry(self):
        from walkabout.core.execute_util import (
            get_renderer_registry,
            set_renderer_registry,
        )

        registry = RendererRegistry()
        set_renderer_registry(registry)
        assert get_renderer_registry() is registry
        set_renderer_registry(None)

    def test_set_renderer_registry_replaces_singleton(self):
        """set_renderer_registry() followed by get_renderer_registry() returns the new instance."""
        from walkabout.core.execute_util import (
            get_renderer_registry,
            set_renderer_registry,
        )

        registry1 = RendererRegistry()
        registry2 = RendererRegistry()

        set_renderer_registry(registry1)
        assert get_renderer_registry() is registry1

        # Replace with a different registry
        set_renderer_registry(registry2)
        assert get_renderer_registry() is registry2
        assert get_renderer_registry() is not registry1

        # Clean up
        set_renderer_registry(None)
