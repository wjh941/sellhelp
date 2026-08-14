import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("view_name", ["Purchase", "Sales", "Returns", "Market", "Pricing"])
def test_product_pickers_request_a_supported_page_size(client, view_name):
    view_source = (PROJECT_ROOT / "frontend" / "src" / "views" / f"{view_name}.vue").read_text(encoding="utf-8")
    match = re.search(r"getProducts\(\{\s*page_size:\s*(\d+)", view_source)

    assert match is not None
    response = client.get("/api/products", params={"page_size": int(match.group(1)), "is_active": "true"})

    assert response.status_code == 200
