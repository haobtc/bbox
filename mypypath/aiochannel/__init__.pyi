from typing import Dict, Any, List, Union, Iterable, Set, Optional

class Channel:
    async def get(self) -> Any: ...
    async def put(self, data:Any) -> None: ...


