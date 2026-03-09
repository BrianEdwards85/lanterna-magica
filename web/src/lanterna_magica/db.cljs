(ns lanterna-magica.db)

(def default-db
  {:current-route    nil

   ;; Dimension types (flat list, ordered by priority)
   :dimension-types       []
   :show-archived-types   false
   :selected-dimension-type-id nil

   ;; Per-type dimension page state, keyed by type id:
   ;; {type-id {:edges [] :page-info {} :search "" :show-archived false}}
   :dimensions-pages      {}

   ;; Per-type dimension lists for dropdowns, keyed by type id:
   ;; {type-id [dim1 dim2 ...]}
   :all-dimensions        {}

   ;; Per-type search results for searchable dropdowns, keyed by type id:
   ;; {type-id [dim1 dim2 ...] | nil}
   :dimensions-search-results {}

   ;; Dialog state for dimension types
   :dimension-type-dialog {:open? false}

   ;; Dialog state for dimensions (any type)
   :dimension-dialog      {:open? false}

   ;; Shared values page
   :shared-values-page  {:edges [] :page-info {:hasNextPage false :endCursor nil}
                         :search "" :show-archived false
                         :selected-id nil
                         :revisions {:edges []}
                         :revisions-page-info nil}

   ;; Configurations page — filter by dimension ids
   :configurations-page {:edges [] :page-info {:hasNextPage false :endCursor nil}
                         :filter-dimension-ids []
                         :selected-id nil :selected nil}

   ;; Dialog state
   :shared-value-dialog {:open? false}
   :revision-dialog     {:open? false}
   :configuration-dialog {:open? false}

   ;; Loading keys (set of keywords) and per-key error map
   :loading          #{}
   :errors           {}})
