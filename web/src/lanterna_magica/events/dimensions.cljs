(ns lanterna-magica.events.dimensions
  (:require [lanterna-magica.events :as-alias events]
            [lanterna-magica.events.helpers :as h]
            [lanterna-magica.gql :as gql]
            [re-frame.core :as rf]
            [re-graph.core :as re-graph]))

(def ^:private page-size 30)

;; ---------------------------------------------------------------------------
;; Dimension Types
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-dimension-types
 (fn [{:keys [db]} _]
   (let [archived (:show-archived-types db)]
     {:db       (h/start-loading db :dimension-types)
      :dispatch [::re-graph/query
                 {:query     gql/dimension-types-query
                  :variables {:includeArchived (boolean archived)}
                  :callback  [::events/on-dimension-types]}]})))

(rf/reg-event-fx
 ::events/on-dimension-types
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         types (or (:dimensionTypes data) [])]
     (cond-> {:db (-> db
                      (assoc :dimension-types types)
                      (h/stop-loading :dimension-types errors))}
       (seq types)
       (assoc :dispatch-n (mapv (fn [dt] [::events/fetch-dimensions-list (:id dt)]) types))))))

(rf/reg-event-fx
 ::events/toggle-dimension-types-archived
 (fn [{:keys [db]} _]
   {:db       (update db :show-archived-types not)
    :dispatch [::events/fetch-dimension-types]}))

;; --- Dimension Type Dialog ---

(rf/reg-event-db
 ::events/open-dimension-type-dialog
 (fn [db _]
   (assoc db :dimension-type-dialog
          {:open?          true
           :dimension-type {:name "" :priority 0}})))

(rf/reg-event-db
 ::events/close-dimension-type-dialog
 (fn [db _]
   (assoc db :dimension-type-dialog {:open? false})))

(rf/reg-event-db
 ::events/set-dimension-type-field
 (fn [db [_ field value]]
   (assoc-in db [:dimension-type-dialog :dimension-type field] value)))

(rf/reg-event-fx
 ::events/save-dimension-type
 (fn [{:keys [db]} _]
   (let [{:keys [dimension-type]} (:dimension-type-dialog db)
         input (select-keys dimension-type [:name :priority])]
     {:db       (h/start-loading db :save-dimension-type)
      :dispatch [::re-graph/mutate
                 {:query     gql/create-dimension-type-mutation
                  :variables {:input input}
                  :callback  [::events/on-dimension-type-saved]}]})))

(rf/reg-event-fx
 ::events/on-dimension-type-saved
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (h/stop-loading db :save-dimension-type errors)}
       {:db       (-> db
                      (h/stop-loading :save-dimension-type)
                      (assoc :dimension-type-dialog {:open? false}))
        :dispatch [::events/fetch-dimension-types]}))))

;; --- Archive / Unarchive Dimension Type ---

(rf/reg-event-fx
 ::events/archive-dimension-type
 (fn [{:keys [db]} [_ id]]
   {:db       (h/start-loading db :archive-dimension-type)
    :dispatch [::re-graph/mutate
               {:query     gql/archive-dimension-type-mutation
                :variables {:id id}
                :callback  [::events/on-dimension-type-archive-toggled]}]}))

(rf/reg-event-fx
 ::events/unarchive-dimension-type
 (fn [{:keys [db]} [_ id]]
   {:db       (h/start-loading db :archive-dimension-type)
    :dispatch [::re-graph/mutate
               {:query     gql/unarchive-dimension-type-mutation
                :variables {:id id}
                :callback  [::events/on-dimension-type-archive-toggled]}]}))

(rf/reg-event-fx
 ::events/on-dimension-type-archive-toggled
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (h/stop-loading db :archive-dimension-type errors)}
       {:db       (h/stop-loading db :archive-dimension-type)
        :dispatch [::events/fetch-dimension-types]}))))

;; ---------------------------------------------------------------------------
;; Dimensions (parameterized by type-id)
;;
;; re-graph callbacks must be [::event {:key val}] — re-graph does
;; (update callback 1 assoc :response response), so index 1 must be a map.
;; We pass type-id inside that map and use rf/unwrap to destructure.
;; ---------------------------------------------------------------------------

(defn- dims-page-path [type-id]
  [:dimensions-pages type-id])

(defn- ensure-page [db type-id]
  (if (get-in db (dims-page-path type-id))
    db
    (assoc-in db (dims-page-path type-id)
              {:edges [] :page-info {:hasNextPage false :endCursor nil}
               :search "" :show-archived false})))

;; --- Fetch dimensions for a type ---

(rf/reg-event-fx
 ::events/fetch-dimensions
 (fn [{:keys [db]} [_ type-id]]
   (let [db       (ensure-page db type-id)
         page     (get-in db (dims-page-path type-id))
         search   (:search page)
         archived (:show-archived page)]
     {:db       (h/start-loading db :dimensions)
      :dispatch [::re-graph/query
                 {:query     gql/dimensions-query
                  :variables {:typeId          type-id
                              :search          (when (seq search) search)

                              :includeArchived (boolean archived)
                              :first           page-size}
                  :callback  [::events/on-dimensions-fresh {:type-id type-id}]}]})))

(rf/reg-event-fx
 ::events/load-more-dimensions
 (fn [{:keys [db]} [_ type-id]]
   (let [page     (get-in db (dims-page-path type-id))
         search   (:search page)
         archived (:show-archived page)
         cursor   (get-in page [:page-info :endCursor])]
     {:db       (h/start-loading db :dimensions)
      :dispatch [::re-graph/query
                 {:query     gql/dimensions-query
                  :variables {:typeId          type-id
                              :search          (when (seq search) search)

                              :includeArchived (boolean archived)
                              :first           page-size
                              :after           cursor}
                  :callback  [::events/on-dimensions-append {:type-id type-id}]}]})))

(rf/reg-event-fx
 ::events/on-dimensions-fresh
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [type-id response]}]
   (let [{:keys [data errors]} response
         connection (:dimensions data)
         path (dims-page-path type-id)]
     {:db (-> db
              (assoc-in (conj path :edges) (:edges connection))
              (assoc-in (conj path :page-info) (:pageInfo connection))
              (h/stop-loading :dimensions errors))})))

(rf/reg-event-fx
 ::events/on-dimensions-append
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [type-id response]}]
   (let [{:keys [data errors]} response
         connection (:dimensions data)
         path (dims-page-path type-id)]
     {:db (-> db
              (update-in (conj path :edges) into (:edges connection))
              (assoc-in (conj path :page-info) (:pageInfo connection))
              (h/stop-loading :dimensions errors))})))

;; --- Search / Archive Toggle ---

(rf/reg-event-fx
 ::events/set-dimensions-search
 (fn [{:keys [db]} [_ type-id text]]
   (let [db   (ensure-page db type-id)
         path (dims-page-path type-id)]
     {:db       (-> db
                    (assoc-in (conj path :search) text)
                    (assoc-in (conj path :edges) [])
                    (assoc-in (conj path :page-info) {:hasNextPage false :endCursor nil}))
      :dispatch [::events/fetch-dimensions type-id]})))

(rf/reg-event-fx
 ::events/toggle-dimensions-archived
 (fn [{:keys [db]} [_ type-id]]
   (let [db   (ensure-page db type-id)
         path (dims-page-path type-id)]
     {:db       (-> db
                    (update-in (conj path :show-archived) not)
                    (assoc-in (conj path :edges) [])
                    (assoc-in (conj path :page-info) {:hasNextPage false :endCursor nil}))
      :dispatch [::events/fetch-dimensions type-id]})))

;; --- Dimension Dialog ---

(rf/reg-event-db
 ::events/open-dimension-dialog
 (fn [db [_ type-id dimension]]
   (assoc db :dimension-dialog
          {:open?     true
           :type-id   type-id
           :editing   (some? dimension)
           :dimension (or dimension {:name "" :description ""})})))

(rf/reg-event-db
 ::events/close-dimension-dialog
 (fn [db _]
   (assoc db :dimension-dialog {:open? false})))

(rf/reg-event-db
 ::events/set-dimension-field
 (fn [db [_ field value]]
   (assoc-in db [:dimension-dialog :dimension field] value)))

(rf/reg-event-fx
 ::events/save-dimension
 (fn [{:keys [db]} _]
   (let [{:keys [editing dimension type-id]} (:dimension-dialog db)
         mutation (if editing gql/update-dimension-mutation gql/create-dimension-mutation)
         input    (if editing
                    (select-keys dimension [:id :name :description])
                    (assoc (select-keys dimension [:name :description])
                           :typeId type-id))]
     {:db       (h/start-loading db :save-dimension)
      :dispatch [::re-graph/mutate
                 {:query     mutation
                  :variables {:input input}
                  :callback  [::events/on-dimension-saved {:type-id type-id}]}]})))

(rf/reg-event-fx
 ::events/on-dimension-saved
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [type-id response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (h/stop-loading db :save-dimension errors)}
       {:db       (-> db
                      (h/stop-loading :save-dimension)
                      (assoc :dimension-dialog {:open? false}))
        :dispatch-n [[::events/fetch-dimensions type-id]
                     [::events/fetch-dimensions-list type-id]]}))))

;; --- Archive / Unarchive Dimension ---

(rf/reg-event-fx
 ::events/archive-dimension
 (fn [{:keys [db]} [_ type-id id]]
   {:db       (h/start-loading db :archive-dimension)
    :dispatch [::re-graph/mutate
               {:query     gql/archive-dimension-mutation
                :variables {:id id}
                :callback  [::events/on-dimension-archive-toggled {:type-id type-id}]}]}))

(rf/reg-event-fx
 ::events/unarchive-dimension
 (fn [{:keys [db]} [_ type-id id]]
   {:db       (h/start-loading db :archive-dimension)
    :dispatch [::re-graph/mutate
               {:query     gql/unarchive-dimension-mutation
                :variables {:id id}
                :callback  [::events/on-dimension-archive-toggled {:type-id type-id}]}]}))

(rf/reg-event-fx
 ::events/on-dimension-archive-toggled
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [type-id response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (h/stop-loading db :archive-dimension errors)}
       {:db       (-> db
                      (h/stop-loading :archive-dimension)
                      (assoc :dimension-dialog {:open? false}))
        :dispatch-n [[::events/fetch-dimensions type-id]
                     [::events/fetch-dimensions-list type-id]]}))))

;; ---------------------------------------------------------------------------
;; Flat dimension lists for dropdowns (per type)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-dimensions-list
 (fn [_ [_ type-id]]
   {:dispatch [::re-graph/query
               {:query     gql/dimensions-query
                :variables {:typeId type-id :first 10}
                :callback  [::events/on-dimensions-list {:type-id type-id}]}]}))

(rf/reg-event-fx
 ::events/on-dimensions-list
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [type-id response]}]
   (let [{:keys [data]} response
         nodes (mapv :node (get-in data [:dimensions :edges]))]
     {:db (assoc-in db [:all-dimensions type-id] nodes)})))

;; ---------------------------------------------------------------------------
;; Search dimensions for dropdowns (per type)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/search-dimensions-list
 (fn [_ [_ type-id query]]
   (if (seq query)
     {:dispatch [::re-graph/query
                 {:query     gql/dimensions-query
                  :variables {:typeId type-id :search query :first 10}
                  :callback  [::events/on-dimensions-search-results {:type-id type-id}]}]}
     {:dispatch [::events/clear-dimensions-search-results type-id]})))

(rf/reg-event-fx
 ::events/on-dimensions-search-results
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [type-id response]}]
   (let [{:keys [data]} response
         nodes (mapv :node (get-in data [:dimensions :edges]))]
     {:db (assoc-in db [:dimensions-search-results type-id] nodes)})))

(rf/reg-event-db
 ::events/clear-dimensions-search-results
 (fn [db [_ type-id]]
   (assoc-in db [:dimensions-search-results type-id] nil)))
