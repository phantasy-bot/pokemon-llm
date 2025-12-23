[**llmletsplay-chronicle-worker**](../../README.md)

***

Defined in: db.ts:1

## Constructors

### Constructor

> **new Database**(`db`): `Database`

Defined in: db.ts:2

#### Parameters

##### db

`D1Database`

#### Returns

`Database`

## Methods

### getAllDrops()

> **getAllDrops**(): `Promise`\<`Record`\<`string`, `unknown`\>[]\>

Defined in: db.ts:4

#### Returns

`Promise`\<`Record`\<`string`, `unknown`\>[]\>

***

### getDrafts()

> **getDrafts**(): `Promise`\<`Record`\<`string`, `unknown`\>[]\>

Defined in: db.ts:18

#### Returns

`Promise`\<`Record`\<`string`, `unknown`\>[]\>

***

### getDrop()

> **getDrop**(`id`): `Promise`\<`Record`\<`string`, `unknown`\> \| `null`\>

Defined in: db.ts:25

#### Parameters

##### id

`string`

#### Returns

`Promise`\<`Record`\<`string`, `unknown`\> \| `null`\>

***

### getDropByAddress()

> **getDropByAddress**(`address`): `Promise`\<`Record`\<`string`, `unknown`\> \| `null`\>

Defined in: db.ts:29

#### Parameters

##### address

`string`

#### Returns

`Promise`\<`Record`\<`string`, `unknown`\> \| `null`\>

***

### insertDrop()

> **insertDrop**(`drop`): `Promise`\<`D1Result`\<`Record`\<`string`, `unknown`\>\>\>

Defined in: db.ts:33

#### Parameters

##### drop

`any`

#### Returns

`Promise`\<`D1Result`\<`Record`\<`string`, `unknown`\>\>\>

***

### updateDrop()

> **updateDrop**(`drop`): `Promise`\<`D1Result`\<`Record`\<`string`, `unknown`\>\>\>

Defined in: db.ts:47

#### Parameters

##### drop

`any`

#### Returns

`Promise`\<`D1Result`\<`Record`\<`string`, `unknown`\>\>\>
