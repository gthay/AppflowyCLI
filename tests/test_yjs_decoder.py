from appflowy_cli import yjs_decoder


def test_unsupported_table_block_is_visible_in_markdown():
    blocks = {
        "page": {"ty": "page", "children": "root"},
        "table": {"ty": "table", "children": "table-children"},
    }
    children = {"root": ["table"], "table-children": []}

    assert yjs_decoder._render_block("page", blocks, {}, children) == [
        "[Unsupported AppFlowy block: table]"
    ]


def test_unsupported_table_block_is_marked_in_json():
    blocks = {"table": {"ty": "table", "children": "children", "data": "{bad"}}
    node = yjs_decoder._block_to_dict("table", blocks, {}, {"children": []})

    assert node["unsupported"] is True
    assert node["raw_data"] == "{bad"
