(ns lanterna-magica.gql
  "GraphQL query and mutation strings for lanterna-magica.")

;; ---------------------------------------------------------------------------
;; Dimension Types
;; ---------------------------------------------------------------------------

(def dimension-types-query
  "query DimensionTypes($includeArchived: Boolean) {
     dimensionTypes(includeArchived: $includeArchived) {
       id name priority createdAt archivedAt
       dimensions(first: 0) { pageInfo { hasNextPage } }
     }
   }")

(def create-dimension-type-mutation
  "mutation CreateDimensionType($input: CreateDimensionTypeInput!) {
     createDimensionType(input: $input) { id name priority createdAt archivedAt }
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
  "query Dimensions($typeId: ID!, $search: String, $includeArchived: Boolean, $first: Int, $after: String) {
     dimensions(typeId: $typeId, search: $search, includeArchived: $includeArchived, first: $first, after: $after) {
       edges { cursor node { id name description base createdAt updatedAt archivedAt type { id name } } }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def dimension-query
  "query Dimension($id: ID!) {
     dimension(id: $id) { id name description base createdAt updatedAt archivedAt type { id name } }
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
;; Services (backward-compat facade)
;; ---------------------------------------------------------------------------

(def services-query
  "query Services($search: String, $includeArchived: Boolean, $first: Int, $after: String) {
     services(search: $search, includeArchived: $includeArchived, first: $first, after: $after) {
       edges { cursor node { id name description createdAt updatedAt archivedAt } }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def service-query
  "query Service($id: ID!) {
     service(id: $id) { id name description createdAt updatedAt archivedAt }
   }")

(def create-service-mutation
  "mutation CreateService($input: CreateServiceInput!) {
     createService(input: $input) { id name description createdAt updatedAt archivedAt }
   }")

(def update-service-mutation
  "mutation UpdateService($input: UpdateServiceInput!) {
     updateService(input: $input) { id name description createdAt updatedAt archivedAt }
   }")

(def archive-service-mutation
  "mutation ArchiveService($id: ID!) {
     archiveService(id: $id) { id name description createdAt updatedAt archivedAt }
   }")

(def unarchive-service-mutation
  "mutation UnarchiveService($id: ID!) {
     unarchiveService(id: $id) { id name description createdAt updatedAt archivedAt }
   }")

;; ---------------------------------------------------------------------------
;; Environments (backward-compat facade)
;; ---------------------------------------------------------------------------

(def environments-query
  "query Environments($search: String, $includeArchived: Boolean, $first: Int, $after: String) {
     environments(search: $search, includeArchived: $includeArchived, first: $first, after: $after) {
       edges { cursor node { id name description createdAt updatedAt archivedAt } }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def environment-query
  "query Environment($id: ID!) {
     environment(id: $id) { id name description createdAt updatedAt archivedAt }
   }")

(def create-environment-mutation
  "mutation CreateEnvironment($input: CreateEnvironmentInput!) {
     createEnvironment(input: $input) { id name description createdAt updatedAt archivedAt }
   }")

(def update-environment-mutation
  "mutation UpdateEnvironment($input: UpdateEnvironmentInput!) {
     updateEnvironment(input: $input) { id name description createdAt updatedAt archivedAt }
   }")

(def archive-environment-mutation
  "mutation ArchiveEnvironment($id: ID!) {
     archiveEnvironment(id: $id) { id name description createdAt updatedAt archivedAt }
   }")

(def unarchive-environment-mutation
  "mutation UnarchiveEnvironment($id: ID!) {
     unarchiveEnvironment(id: $id) { id name description createdAt updatedAt archivedAt }
   }")

;; ---------------------------------------------------------------------------
;; Shared Values
;; ---------------------------------------------------------------------------

(def shared-values-query
  "query SharedValues($includeArchived: Boolean, $first: Int, $after: String) {
     sharedValues(includeArchived: $includeArchived, first: $first, after: $after) {
       edges { cursor node { id name createdAt updatedAt archivedAt } }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def shared-value-query
  "query SharedValue($id: ID!, $dimensionIds: [ID!], $includeBase: Boolean, $currentOnly: Boolean, $first: Int, $after: String) {
     sharedValue(id: $id) {
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

;; ---------------------------------------------------------------------------
;; Configurations
;; ---------------------------------------------------------------------------

(def configurations-query
  "query Configurations($dimensionIds: [ID!], $includeBase: Boolean, $first: Int, $after: String) {
     configurations(dimensionIds: $dimensionIds, includeBase: $includeBase, first: $first, after: $after) {
       edges {
         cursor
         node {
           id body isCurrent createdAt
           dimensions { id name type { id name } }
         }
       }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def configuration-query
  "query Configuration($id: ID!) {
     configuration(id: $id) {
       id body isCurrent createdAt
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
       id body isCurrent createdAt
       dimensions { id name type { id name } }
       substitutions {
         id jsonpath createdAt
         sharedValue { id name }
       }
     }
   }")

(def update-config-substitution-mutation
  "mutation UpdateConfigSubstitution($input: SetConfigSubstitutionInput!) {
     updateConfigSubstitution(input: $input) {
       id jsonpath createdAt
       configuration { id }
       sharedValue { id name }
     }
   }")
