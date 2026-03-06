(ns lanterna-magica.gql
  "GraphQL query and mutation strings for lanterna-magica.")

;; ---------------------------------------------------------------------------
;; Services
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
;; Environments
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

(def search-shared-values-query
  "query SearchSharedValues($search: String!, $includeArchived: Boolean, $limit: Int) {
     searchSharedValues(search: $search, includeArchived: $includeArchived, limit: $limit) {
       id name createdAt updatedAt archivedAt
     }
   }")

(def shared-value-query
  "query SharedValue($id: ID!, $serviceId: ID, $environmentId: ID, $includeGlobal: Boolean, $currentOnly: Boolean, $first: Int, $after: String) {
     sharedValue(id: $id) {
       id name createdAt updatedAt archivedAt
       revisions(serviceId: $serviceId, environmentId: $environmentId, includeGlobal: $includeGlobal, currentOnly: $currentOnly, first: $first, after: $after) {
         edges {
           cursor
           node {
             id value isCurrent createdAt
             service { id name }
             environment { id name }
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
       service { id name }
       environment { id name }
     }
   }")

;; ---------------------------------------------------------------------------
;; Configurations
;; ---------------------------------------------------------------------------

(def configurations-query
  "query Configurations($serviceId: ID, $environmentId: ID, $includeGlobal: Boolean, $first: Int, $after: String) {
     configurations(serviceId: $serviceId, environmentId: $environmentId, includeGlobal: $includeGlobal, first: $first, after: $after) {
       edges {
         cursor
         node {
           id body isCurrent createdAt
           service { id name }
           environment { id name }
         }
       }
       pageInfo { hasNextPage endCursor }
     }
   }")

(def configuration-query
  "query Configuration($id: ID!) {
     configuration(id: $id) {
       id body isCurrent createdAt
       service { id name }
       environment { id name }
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
       service { id name }
       environment { id name }
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
