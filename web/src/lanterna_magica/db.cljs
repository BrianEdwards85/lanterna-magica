(ns lanterna-magica.db)

(def default-db
  {:current-route    nil

   ;; Entity page state — holds edges, page-info, search, filters
   :services-page       {:edges [] :page-info {:hasNextPage false :endCursor nil}
                          :search "" :show-archived false}
   :environments-page   {:edges [] :page-info {:hasNextPage false :endCursor nil}
                          :search "" :show-archived false}
   :shared-values-page  {:edges [] :page-info {:hasNextPage false :endCursor nil}
                          :search "" :show-archived false
                          :selected-id nil
                          :revisions {:edges []}
                          :revisions-page-info nil}
   :configurations-page {:edges [] :page-info {:hasNextPage false :endCursor nil}
                          :filter-service-id nil :filter-environment-id nil
                          :selected-id nil :selected nil}

   ;; Flat lists for dropdowns (initial set, no pagination)
   :all-services     []
   :all-environments []

   ;; Search results for searchable dropdowns
   :services-search-results     nil
   :environments-search-results nil

   ;; Dialog state per entity
   :service-dialog      {:open? false}
   :environment-dialog  {:open? false}
   :shared-value-dialog {:open? false}
   :revision-dialog     {:open? false}
   :configuration-dialog {:open? false}

   ;; Loading keys (set of keywords) and per-key error map
   :loading          #{}
   :errors           {}})
