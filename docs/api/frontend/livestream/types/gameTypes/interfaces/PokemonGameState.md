[**pokemon-ui**](../../../README.md)

***

Defined in: types/gameTypes.ts:146

## Extended by

- [`GameState`](GameState.md)

## Properties

### actions

> **actions**: `number`

Defined in: types/gameTypes.ts:188

***

### animateActions?

> `optional` **animateActions**: `number`

Defined in: types/gameTypes.ts:242

***

### avgCycleTime?

> `optional` **avgCycleTime**: `number`

Defined in: types/gameTypes.ts:197

***

### badgeDetails?

> `optional` **badgeDetails**: [`Badge`](Badge.md)[]

Defined in: types/gameTypes.ts:149

***

### badges

> **badges**: [`BadgeType`](../type-aliases/BadgeType.md)[]

Defined in: types/gameTypes.ts:148

***

### battleForecast?

> `optional` **battleForecast**: [`BattleForecast`](BattleForecast.md)

Defined in: types/gameTypes.ts:183

***

### battleType?

> `optional` **battleType**: `"Wild"` \| `"Trainer"` \| `"Gym"` \| `"Elite Four"` \| `"Champion"`

Defined in: types/gameTypes.ts:185

***

### cameraPosition?

> `optional` **cameraPosition**: \[`number`, `number`\]

Defined in: types/gameTypes.ts:169

***

### currentCycleTime?

> `optional` **currentCycleTime**: `number`

Defined in: types/gameTypes.ts:195

***

### currentLocation?

> `optional` **currentLocation**: `string`

Defined in: types/gameTypes.ts:160

***

### currentTeam

> **currentTeam**: [`Pokemon`](Pokemon.md)[]

Defined in: types/gameTypes.ts:175

***

### cursorPosition?

> `optional` **cursorPosition**: \[`number`, `number`\]

Defined in: types/gameTypes.ts:168

***

### cycle

> **cycle**: `number`

Defined in: types/gameTypes.ts:189

***

### cycleMetrics?

> `optional` **cycleMetrics**: `object`

Defined in: types/gameTypes.ts:200

#### diff?

> `optional` **diff**: `number`

#### llm?

> `optional` **llm**: `number`

#### mGBA?

> `optional` **mGBA**: `number`

#### total?

> `optional` **total**: `number`

#### vision?

> `optional` **vision**: `number`

***

### cyclesEnabled?

> `optional` **cyclesEnabled**: `boolean`

Defined in: types/gameTypes.ts:199

***

### cycleTiming?

> `optional` **cycleTiming**: `string`

Defined in: types/gameTypes.ts:194

***

### debugMode?

> `optional` **debugMode**: `boolean`

Defined in: types/gameTypes.ts:241

***

### enemyPokemon?

> `optional` **enemyPokemon**: [`Pokemon`](Pokemon.md)[]

Defined in: types/gameTypes.ts:178

***

### explorationPct?

> `optional` **explorationPct**: `number`

Defined in: types/gameTypes.ts:170

***

### gameStatus

> **gameStatus**: `string`

Defined in: types/gameTypes.ts:190

***

### goals

> **goals**: `object`

Defined in: types/gameTypes.ts:152

#### primary

> **primary**: `string`

#### secondary

> **secondary**: `string` \| `string`[]

#### tertiary

> **tertiary**: `string`

***

### inBattle?

> `optional` **inBattle**: `boolean`

Defined in: types/gameTypes.ts:184

***

### inMenu?

> `optional` **inMenu**: `boolean`

Defined in: types/gameTypes.ts:209

***

### lassMarkings?

> `optional` **lassMarkings**: [`LassMarking`](LassMarking.md)[]

Defined in: types/gameTypes.ts:171

***

### llmMetrics?

> `optional` **llmMetrics**: `object`

Defined in: types/gameTypes.ts:243

#### p50LatencySec?

> `optional` **p50LatencySec**: `number`

#### p95LatencySec?

> `optional` **p95LatencySec**: `number`

#### successRate?

> `optional` **successRate**: `number`

***

### locationDetails?

> `optional` **locationDetails**: [`LocationInfo`](LocationInfo.md)

Defined in: types/gameTypes.ts:161

***

### mapHeight?

> `optional` **mapHeight**: `number`

Defined in: types/gameTypes.ts:167

***

### mapWidth?

> `optional` **mapWidth**: `number`

Defined in: types/gameTypes.ts:166

***

### menuType?

> `optional` **menuType**: `string`

Defined in: types/gameTypes.ts:210

***

### minimapGridSize?

> `optional` **minimapGridSize**: `object`

Defined in: types/gameTypes.ts:172

#### height

> **height**: `number`

#### width

> **width**: `number`

***

### minimapLocation

> **minimapLocation**: `string`

Defined in: types/gameTypes.ts:164

***

### minimapSrc?

> `optional` **minimapSrc**: `string`

Defined in: types/gameTypes.ts:239

***

### minimapTimestamp?

> `optional` **minimapTimestamp**: `number`

Defined in: types/gameTypes.ts:165

***

### minimapVisible

> **minimapVisible**: `boolean`

Defined in: types/gameTypes.ts:240

***

### modelName

> **modelName**: `string`

Defined in: types/gameTypes.ts:192

***

### movementState?

> `optional` **movementState**: `object`

Defined in: types/gameTypes.ts:218

#### bike\_speed

> **bike\_speed**: `number`

#### is\_biking

> **is\_biking**: `boolean`

#### is\_surfing

> **is\_surfing**: `boolean`

#### movement\_mode

> **movement\_mode**: `"walking"` \| `"biking"` \| `"surfing"`

#### movement\_status

> **movement\_status**: `number`

#### picture\_id

> **picture\_id**: `number`

#### sprite\_image\_idx

> **sprite\_image\_idx**: `number`

***

### nameEntryState?

> `optional` **nameEntryState**: \{ `cursor_index`: `number`; `cursor_x`: `number`; `cursor_y`: `number`; `grid_size`: `number`; `is_name_entry`: `boolean`; `selected_char`: `string`; \} \| `null`

Defined in: types/gameTypes.ts:228

***

### otherGoals

> **otherGoals**: `string`

Defined in: types/gameTypes.ts:157

***

### party?

> `optional` **party**: [`Pokemon`](Pokemon.md)[]

Defined in: types/gameTypes.ts:176

***

### pcBox?

> `optional` **pcBox**: [`Pokemon`](Pokemon.md)[]

Defined in: types/gameTypes.ts:177

***

### prevCycleTime?

> `optional` **prevCycleTime**: `number`

Defined in: types/gameTypes.ts:196

***

### processingStatus?

> `optional` **processingStatus**: `string`

Defined in: types/gameTypes.ts:191

***

### screenshotUrl?

> `optional` **screenshotUrl**: `string`

Defined in: types/gameTypes.ts:238

***

### selectedPokemon?

> `optional` **selectedPokemon**: [`Pokemon`](Pokemon.md)

Defined in: types/gameTypes.ts:182

***

### sessionStartTime?

> `optional` **sessionStartTime**: `number`

Defined in: types/gameTypes.ts:198

***

### textState?

> `optional` **textState**: `object`

Defined in: types/gameTypes.ts:212

#### is\_printing

> **is\_printing**: `boolean`

#### text\_flags

> **text\_flags**: `number`

#### text\_speed

> **text\_speed**: `number`

***

### tokensUsed

> **tokensUsed**: `number`

Defined in: types/gameTypes.ts:193

***

### wildPokemon?

> `optional` **wildPokemon**: [`Pokemon`](Pokemon.md)[]

Defined in: types/gameTypes.ts:179
