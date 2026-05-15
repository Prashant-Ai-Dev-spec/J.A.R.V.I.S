from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from . import actions

router = APIRouter()

class CustomInvoke(BaseModel):
    action: str
    params: Dict[str, Any] = {}

@router.post('/invoke')
def invoke_custom(payload: CustomInvoke):
    action = payload.action
    params = payload.params or {}
    if action == 'find_image':
        img_b64 = params.get('image_b64')
        conf = float(params.get('confidence', 0.8))
        return actions.find_image(img_b64, confidence=conf)
    elif action == 'typed_mouse':
        steps = params.get('steps', [])
        return actions.typed_mouse_flow(steps)
    else:
        return {'error': 'unsupported custom action'}
