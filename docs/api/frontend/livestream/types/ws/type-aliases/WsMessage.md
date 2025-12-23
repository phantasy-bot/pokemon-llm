[**pokemon-ui**](../../../README.md)

***

> **WsMessage** = \{ `payload`: [`StateUpdatePayload`](../interfaces/StateUpdatePayload.md); `type`: `"state_update"`; \} \| \{ `payload`: [`StateUpdatePayload`](../interfaces/StateUpdatePayload.md); `type`: `"state_snapshot"`; \} \| \{ `payload`: [`LogEntryPayload`](../interfaces/LogEntryPayload.md); `type`: `"log_entry"`; \} \| \{ `payload`: [`VisionPayload`](../interfaces/VisionPayload.md); `type`: `"vision_update"`; \} \| \{ `payload`: [`VisionPayload`](../interfaces/VisionPayload.md); `type`: `"vision_status"`; \} \| \{ `payload`: [`MemoryWritePayload`](../interfaces/MemoryWritePayload.md); `type`: `"memory_write"`; \} \| \{ `payload?`: `unknown`; `type?`: `string`; \}

Defined in: types/ws.ts:38
