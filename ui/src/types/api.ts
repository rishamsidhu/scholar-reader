/**
 * The design of the data types for responses roughly follow the conventions of JSON:API:
 * See the specification at https://jsonapi.org/format/.
 *
 * In addition, field names are written using underscores, not camelCase.
 *
 * These data structures roughly resemble the schemas in the database. A definition of the schemas along
 * with documentation should reside in 'data-processing/common/models.py' or thereabouts.
 *
 * This file was intended to be copied and pasted into other projects that need to know the types
 * returned from the API. Because of this, all types are exported, so that when this file is copied
 * into other projects, all of the types are available to the client code.
 */

export interface PaperIdWithCounts {
  s2Id: string;
  arxivId?: string;
  extractedSymbolCount: number;
  extractedCitationCount: number;
}

/**
 * Format of returned papers loosely follows that for the S2 API:
 * https://api.semanticscholar.org/
 */
export interface Paper {
  s2Id: string;
  abstract: string;
  authors: Author[];
  title: string;
  url: string;
  venue: string;
  year: number | null;
  influentialCitationCount?: number;
  citationVelocity?: number;
}

export interface Author {
  id: string;
  name: string;
  url: string;
}

export interface EntityGetResponse {
  data?: Entity[];
}

/**
 * Use type guards (e.g., 'isSymbol') to distinguish between types of entities.
 */
export type Entity = GenericEntity | Symbol | Citation | Sentence;

/**
 * All entity specifications should extend BaseEntity. To make specific relationship properties
 * known to TypeScript, define a relationships type (e.g., see 'SymbolRelationships'), and
 * pass it as the first generic parameter. Otherwise, set the generic to '{}'.
 */
export interface BaseEntity {
  /**
   * Entity IDs are guaranteed to be unique, both within and across papers.
   */
  id: string;
  type: string;
  attributes: BaseEntityAttributes;
  relationships: Relationships;
}

/**
 * All entities must define at least these attributes.
 */
export interface BaseEntityAttributes {
  version: number;
  source: string;
  bounding_boxes: BoundingBox[];
}

/**
 * List of base entity attribute keys. Update this as 'BaseEntityAttributes' updates. This list
 * lets a program check statically whether an attribute on an entity is a custom attribute.
 */
export const BASE_ENTITY_ATTRIBUTE_KEYS = [
  "id",
  "type",
  "version",
  "source",
  "bounding_boxes",
];

/**
 * While it is not described with types here, Relationships must be key-value pairs, where the values
 * are either 'Relationship' or a list of 'Relationship's.
 */
export interface Relationships {}

export interface Relationship {
  type: string;
  id: string | null;
}

export function isRelationship(o: any): o is Relationship {
  return typeof o.type === "string" && typeof o.id === "string";
}

/**
 * An entity where no information is known about its type, and hence attributes and
 * relationships specific to that entity type are not available. This type is defined to provide
 * *some* small amount of type checking for unknown and new types of entities.
 */
export interface GenericEntity extends BaseEntity {
  attributes: BaseEntityAttributes & GenericAttributes;
  relationships: GenericRelationships;
}

/**
 * When posting an entity, an 'id' need not be included, nor a version tag.
 */
export interface EntityCreatePayload {
  data: EntityCreateData;
}

export interface EntityCreateData {
  type: string;
  attributes: Omit<BaseEntityAttributes, "version"> & GenericAttributes;
  relationships: GenericRelationships;
}

/**
 * When patching an entity, the 'type' and 'id' are required. The 'source' attribute is also
 * required. All modified entities and specified bounding boxes and data will be assigned the
 * the provided 'source' value.
 */
export interface EntityUpdatePayload {
  data: EntityUpdateData;
}

export interface EntityUpdateData {
  id: string;
  type: string;
  attributes: Pick<GenericAttributes, "source"> & Partial<GenericAttributes>;
  relationships?: Partial<GenericRelationships>;
}

/**
 * In general, attributes can have values of type 'string | number | string[] | null | undefined'. Because
 * we're doing a type intersection with BaseEntityAttributes above to define the attributes for
 * a BasicEntity (where some properties are of other types like BoundingBox[]), 'any' is used as
 * the type of value here, even though the types of GenericAttributes values should be restricted.
 */
export interface GenericAttributes {
  [key: string]: any;
}

export type GenericRelationships = {
  [key: string]: Relationship | Relationship[];
};

/**
 * 'Symbol' is an example of how to define a new entity type with custom attributes
 * and relationships. Note that a full custom entity definition includes:
 * * an 'attributes' type
 * * a 'relationships' type
 * * a type-guard (i.e., an 'is<Entity>' function)
 */
export interface Symbol extends BaseEntity {
  type: "symbol";
  attributes: SymbolAttributes;
  relationships: SymbolRelationships;
}

export interface SymbolAttributes extends BaseEntityAttributes {
  tex: string | null;
  name: string | null;
  definition: string | null;
  equation: string | null;
  passages: string[];
  mathml: string | null;
  mathml_near_matches: string[];
}

export interface SymbolRelationships {
  sentence: Relationship;
  children: Relationship[];
}

/**
 * Type guards for entities should only have to check the 'type' attribute.
 */
export function isSymbol(entity: Entity): entity is Symbol {
  return entity.type === "symbol";
}

export interface Term extends BaseEntity {
  type: "term";
  attributes: TermAttributes;
  relationships: {};
}

export interface TermAttributes extends BaseEntityAttributes {
  name: string | null;
  definitions: string[];
  sources: string[];
}

export function isTerm(entity: Entity): entity is Term {
  return entity.type === "term";
}

export interface Citation extends BaseEntity {
  type: "citation";
  attributes: CitationAttributes;
  relationships: {};
}

export interface CitationAttributes extends BaseEntityAttributes {
  paper_id: string | null;
}

export function isCitation(entity: Entity): entity is Citation {
  return entity.type === "citation";
}

export interface Sentence extends BaseEntity {
  type: "sentence";
  attributes: SentenceAttributes;
  relationships: {};
}

export interface SentenceAttributes extends BaseEntityAttributes {
  text: string | null;
  tex: string | null;
  tex_start: number | null;
  tex_end: number | null;
}

export function isSentence(entity: Entity): entity is Sentence {
  return entity.type === "sentence";
}

/**
 * Matches the schema of the data in the 'boundingbox' table in the database.  'left', 'top',
 * 'width', and 'height' are expressed in ratios to the page width and height, rather than
 * absolute coordinates.
 *
 * For example, a bounding box is expressed as
 * {
 *   left: .1,
 *   right: .1,
 *   width: .2,
 *   height: .05
 * }
 *
 * if its absolute position is (50px, 100px), its width is (100px), and its
 * height is (50px) on a page with dimensions (W = 500px, H = 1000px).
 *
 * This representation of coordinates was chosen due to constraints in the design of the data
 * processing pipeline. More specifically, it's easier to extract ratio coordinates than absolute
 * coordinates when processing PDFs and PostScript files with Python.
 */
export interface BoundingBox {
  source: string;
  /**
   * Page indexes start at 0.
   */
  page: number;
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface PaperWithEntityCounts {
  s2_id: string;
  arxiv_id?: string;
  citations: string;
  symbols: string;
}
