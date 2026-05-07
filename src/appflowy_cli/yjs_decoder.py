import json
import pycrdt


def _load_doc(doc_state: list[int] | bytes):
    doc = pycrdt.Doc()
    doc.apply_update(bytes(doc_state))

    root = doc.get('data', type=pycrdt.Map)
    document = root['document']
    meta = document['meta']
    text_map = meta['text_map']
    children_map_raw = meta['children_map']
    blocks_raw = document['blocks']

    texts = {}
    for k in text_map:
        texts[k] = str(text_map[k])

    children = {}
    for k in children_map_raw:
        v = children_map_raw[k]
        children[k] = list(v) if isinstance(v, pycrdt.Array) else v

    blocks = {}
    for k in blocks_raw:
        b = blocks_raw[k]
        if isinstance(b, pycrdt.Map):
            blocks[k] = {bk: b[bk] for bk in b}

    page_block_id = None
    for bid, b in blocks.items():
        if b.get('ty') == 'page':
            page_block_id = bid
            break

    if not page_block_id:
        page_block_id = document['page_id']

    return blocks, texts, children, page_block_id


def decode_document(doc_state: list[int] | bytes) -> str:
    blocks, texts, children, page_block_id = _load_doc(doc_state)
    lines = _render_block(page_block_id, blocks, texts, children, indent=0)
    return '\n'.join(lines).strip()


def decode_document_json(doc_state: list[int] | bytes) -> list[dict]:
    blocks, texts, children, page_block_id = _load_doc(doc_state)
    return _block_to_dict(page_block_id, blocks, texts, children).get("children", [])


def _block_to_dict(block_id, blocks, texts, children):
    block = blocks.get(block_id, {})
    ty = block.get('ty', '')
    ext_id = block.get('external_id', '')
    text = texts.get(ext_id, '')
    bdata = _parse_block_data(block.get('data'))

    node = {"type": ty, "text": text, "id": block_id}
    if bdata:
        node["data"] = bdata
    elif block.get('data'):
        node["raw_data"] = block.get('data')
    if ty in {'table', 'table/cell'}:
        node["unsupported"] = True

    child_key = block.get('children', '')
    child_ids = children.get(child_key, [])
    if child_ids:
        node["children"] = [_block_to_dict(cid, blocks, texts, children) for cid in child_ids]

    return node


def _parse_block_data(data_str):
    try:
        return json.loads(data_str) if data_str else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _render_block(block_id, blocks, texts, children, indent=0):
    block = blocks.get(block_id, {})
    ty = block.get('ty', '')
    ext_id = block.get('external_id', '')
    text = texts.get(ext_id, '')
    bdata = _parse_block_data(block.get('data'))

    lines = []
    pad = '  ' * indent

    if ty == 'page':
        pass
    elif ty == 'heading':
        level = bdata.get('level', 1)
        lines.append(f'{"#" * level} {text}')
    elif ty == 'paragraph':
        lines.append(f'{pad}{text}')
    elif ty == 'bulleted_list':
        lines.append(f'{pad}- {text}')
    elif ty == 'numbered_list':
        lines.append(f'{pad}1. {text}')
    elif ty == 'todo_list':
        mark = '[x]' if bdata.get('checked') else '[ ]'
        lines.append(f'{pad}{mark} {text}')
    elif ty == 'quote':
        lines.append(f'{pad}> {text}')
    elif ty == 'divider':
        lines.append('---')
    elif ty == 'code':
        lang = bdata.get('language', '')
        lines.append(f'{pad}```{lang}')
        lines.append(text)
        lines.append(f'{pad}```')
    elif ty == 'callout':
        lines.append(f'{pad}> **Note:** {text}')
    elif ty == 'toggle_list':
        lines.append(f'{pad}<details><summary>{text}</summary>')
    elif ty == 'image':
        url = bdata.get('url', '')
        lines.append(f'{pad}![image]({url})')
    elif ty == 'math_equation':
        lines.append(f'{pad}$$\n{text}\n$$')
    elif ty == 'table':
        lines.append(f'{pad}[Unsupported AppFlowy block: table]')
    elif ty == 'table/cell':
        display = text or '[empty cell]'
        lines.append(f'{pad}[Unsupported AppFlowy table cell: {display}]')
    else:
        if text:
            lines.append(f'{pad}{text}')

    child_key = block.get('children', '')
    child_ids = children.get(child_key, [])
    for cid in child_ids:
        child_indent = indent + (1 if ty not in ('page',) else 0)
        lines.extend(_render_block(cid, blocks, texts, children, child_indent))

    if ty == 'toggle_list':
        lines.append(f'{pad}</details>')

    return lines
