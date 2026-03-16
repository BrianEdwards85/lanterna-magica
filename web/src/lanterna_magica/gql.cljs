(ns lanterna-magica.gql
  "GraphQL query and mutation strings for lanterna-magica.")

;; ---------------------------------------------------------------------------
;; Dimension Types
;; ---------------------------------------------------------------------------

(def dimension-types-query
  "query DimensionTypes($includeArchived: Boolean) {
     dimensionTypes(includeArchived: $includeArchived) {
       id name priority createdAt archivedAt
     }
   }")

(def create-dimension-type-mutation
  "mutation CreateDimensionType($input: CreateDimensionTypeInput!) {
     createDimensionType(input: $input) { id name priority createdAt archivedAt }
   }")

(def update-dimension-type-mutation
  "mutation UpdateDimensionType($input: UpdateDimensionTypeInput!) {
     updateDimensionType(input: $input) { id name priority createdAt archivedAt }
   }")

(def swap-dimension-type-priorities-mutation
  "mutation SwapDimensionTypePriorities($idA: ID!, $idB: ID!) {
     swapDimensionTypePriorities(idA: $idA, idB: $idB) { id name priority createdAt archivedAt }
   }")

(def archive-dimension-type-mutation
  "mutation ArchiveDimensionType($id: ID!) {
     archiveDimensionType(id: $id) { id name priority createdAt archivedAt }
   }")

(def unarchive-dimension-type-mutation
  "mutation UnarchiveDimensionType($id: ID!) {
     unarchiveDimensionType(id: $id) { id name priority createdAt archivedAt }
   }")

;; ---------------------------------------------------------------------------
;; Dimensions
;; ---------------------------------------------------------------------------

(def dimensions-query
  "query Dimensions($typeId: ID!, $search: String, $includeBase: Boolean, $includeArchived: Boolean, $first: Int, $after: String) {
     dimensions(typeId: $typeId, search: $search, includeBase: $includeBase, includeArchived: $includeArchived, first: $first, after: $after) {
       edges { cursor node { id name description base createdAt updatedAt archivedAt type { id name } } }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def create-dimension-mutation
  "mutation CreateDimension($input: CreateDimensionInput!) {
     createDimension(input: $input) { id name description base createdAt updatedAt archivedAt type { id name } }
   }")

(def update-dimension-mutation
  "mutation UpdateDimension($input: UpdateDimensionInput!) {
     updateDimension(input: $input) { id name description base createdAt updatedAt archivedAt type { id name } }
   }")

(def archive-dimension-mutation
  "mutation ArchiveDimension($id: ID!) {
     archiveDimension(id: $id) { id name description base createdAt updatedAt archivedAt type { id name } }
   }")

(def unarchive-dimension-mutation
  "mutation UnarchiveDimension($id: ID!) {
     unarchiveDimension(id: $id) { id name description base createdAt updatedAt archivedAt type { id name } }
   }")

;; ---------------------------------------------------------------------------
;; Shared Values
;; ---------------------------------------------------------------------------

(def shared-values-query
  "query SharedValues($includeArchived: Boolean, $search: String, $first: Int, $after: String) {
     sharedValues(includeArchived: $includeArchived, search: $search, first: $first, after: $after) {
       edges { cursor node { id name createdAt updatedAt archivedAt } }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def shared-value-query
  "query SharedValuesByIds($ids: [ID!]!, $dimensionIds: [ID!], $includeBase: Boolean, $currentOnly: Boolean, $first: Int, $after: String) {
     sharedValuesByIds(ids: $ids) {
       id name createdAt updatedAt archivedAt
       revisions(dimensionIds: $dimensionIds, includeBase: $includeBase, currentOnly: $currentOnly, first: $first, after: $after) {
         edges {
           cursor
           node {
             id value isCurrent createdAt
             dimensions { id name type { id name } }
           }
         }
         pageInfo { hasNextPage endCursor }
       }
       usedBy(first: 20) {
         edges {
           node {
             id isCurrent createdAt
             dimensions { id name type { id name } }
           }
         }
         pageInfo { hasNextPage endCursor }
       }
     }
   }")

(def create-shared-value-mutation
  "mutation CreateSharedValue($input: CreateSharedValueInput!) {
     createSharedValue(input: $input) { id name createdAt updatedAt archivedAt }
   }")

(def update-shared-value-mutation
  "mutation UpdateSharedValue($input: UpdateSharedValueInput!) {
     updateSharedValue(input: $input) { id name createdAt updatedAt archivedAt }
   }")

(def archive-shared-value-mutation
  "mutation ArchiveSharedValue($id: ID!) {
     archiveSharedValue(id: $id) { id name createdAt updatedAt archivedAt }
   }")

(def unarchive-shared-value-mutation
  "mutation UnarchiveSharedValue($id: ID!) {
     unarchiveSharedValue(id: $id) { id name createdAt updatedAt archivedAt }
   }")

(def create-shared-value-revision-mutation
  "mutation CreateSharedValueRevision($input: CreateSharedValueRevisionInput!) {
     createSharedValueRevision(input: $input) {
       id value isCurrent createdAt
       sharedValue { id name }
       dimensions { id name type { id name } }
     }
   }")

(def set-revision-current-mutation
  "mutation SetRevisionCurrent($id: ID!, $isCurrent: Boolean!) {
     setRevisionCurrent(id: $id, isCurrent: $isCurrent) {
       id value isCurrent createdAt
       dimensions { id name type { id name } }
     }
   }")

;; ---------------------------------------------------------------------------
;; Configurations
;; ---------------------------------------------------------------------------

(def extract-sentinel-paths-query
  "query ExtractSentinelPaths($body: JSON!) {
     extractSentinelPaths(body: $body)
   }")

(def configurations-query
  "query Configurations($dimensionIds: [ID!], $includeBase: Boolean, $currentOnly: Boolean, $first: Int, $after: String) {
     configurations(dimensionIds: $dimensionIds, includeBase: $includeBase, currentOnly: $currentOnly, first: $first, after: $after) {
       edges {
         cursor
         node {
           id body isCurrent createdAt projection
           dimensions { id name type { id name } }
         }
       }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def configuration-query
  "query ConfigurationsByIds($ids: [ID!]!) {
     configurationsByIds(ids: $ids) {
       id body isCurrent createdAt projection
       dimensions { id name type { id name } }
       substitutions {
         id jsonpath createdAt
         sharedValue { id name }
       }
     }
   }")

(def create-configuration-mutation
  "mutation CreateConfiguration($input: CreateConfigurationInput!) {
     createConfiguration(input: $input) {
       id body isCurrent createdAt projection
       dimensions { id name type { id name } }
       substitutions {
         id jsonpath createdAt
         sharedValue { id name }
       }
     }
   }")

(def set-configuration-current-mutation
  "mutation SetConfigurationCurrent($id: ID!, $isCurrent: Boolean!) {
     setConfigurationCurrent(id: $id, isCurrent: $isCurrent) {
       id body isCurrent createdAt projection
       dimensions { id name type { id name } }
     }
   }")

(def resolve-shared-value-query
  "query ResolveSharedValue($sharedValueId: ID!, $dimensionIds: [ID!]!) {
     resolveSharedValue(sharedValueId: $sharedValueId, dimensionIds: $dimensionIds) {
       id
       value
     }
   }")

;; ---------------------------------------------------------------------------
;; Outputs
;; ---------------------------------------------------------------------------

(def outputs-query
  "query Outputs($includeArchived: Boolean, $first: Int, $after: String) {
     outputs(includeArchived: $includeArchived, first: $first, after: $after) {
       edges {
         cursor
         node {
           id pathTemplate format createdAt updatedAt archivedAt
           dimensions { id name type { id name } }
           results { id succeeded writtenAt }
         }
       }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def output-query
  "query OutputsByIds($ids: [ID!]!) {
     outputsByIds(ids: $ids) {
       id pathTemplate format createdAt updatedAt archivedAt
       dimensions { id name type { id name } }
       results {
         id scopeHash path content succeeded error writtenAt writtenBy
       }
     }
   }")

(def create-output-mutation
  "mutation CreateOutput($input: CreateOutputInput!) {
     createOutput(input: $input) {
       id pathTemplate format createdAt updatedAt archivedAt
       dimensions { id name type { id name } }
     }
   }")

(def archive-output-mutation
  "mutation ArchiveOutput($id: ID!) {
     archiveOutput(id: $id) {
       id pathTemplate format createdAt updatedAt archivedAt
       dimensions { id name type { id name } }
     }
   }")

(def trigger-output-mutation
  "mutation TriggerOutput($id: ID!) {
     triggerOutput(id: $id) {
       id pathTemplate format createdAt updatedAt archivedAt
       dimensions { id name type { id name } }
       results {
         id scopeHash path content succeeded error writtenAt writtenBy
       }
     }
   }")
