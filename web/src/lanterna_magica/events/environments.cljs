(ns lanterna-magica.events.environments
  (:require [lanterna-magica.events :as-alias events]
            [lanterna-magica.gql :as gql]
            [re-frame.core :as rf]
            [re-graph.core :as re-graph]))

(def ^:private page-size 30)

;; ---------------------------------------------------------------------------
;; Fetch Environments (paginated list)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-environments
 (fn [{:keys [db]} _]
   (let [search   (get-in db [:environments-page :search])
         archived (get-in db [:environments-page :show-archived])]
     {:db       (update db :loading conj :environments)
      :dispatch [::re-graph/query
                 {:query     gql/environments-query
                  :variables {:search          (when (seq search) search)
                              :includeArchived (boolean archived)
                              :first           page-size}
                  :callback  [::events/on-environments-fresh]}]})))

(rf/reg-event-fx
 ::events/load-more-environments
 (fn [{:keys [db]} _]
   (let [search   (get-in db [:environments-page :search])
         archived (get-in db [:environments-page :show-archived])
         cursor   (get-in db [:environments-page :page-info :endCursor])]
     {:db       (update db :loading conj :environments)
      :dispatch [::re-graph/query
                 {:query     gql/environments-query
                  :variables {:search          (when (seq search) search)
                              :includeArchived (boolean archived)
                              :first           page-size
                              :after           cursor}
                  :callback  [::events/on-environments-append]}]})))

(rf/reg-event-fx
 ::events/on-environments-fresh
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:environments data)]
     {:db (-> db
              (assoc-in [:environments-page :edges] (:edges connection))
              (assoc-in [:environments-page :page-info] (:pageInfo connection))
              (update :loading disj :environments)
              (assoc-in [:errors :environments] errors))})))

(rf/reg-event-fx
 ::events/on-environments-append
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:environments data)]
     {:db (-> db
              (update-in [:environments-page :edges] into (:edges connection))
              (assoc-in [:environments-page :page-info] (:pageInfo connection))
              (update :loading disj :environments)
              (assoc-in [:errors :environments] errors))})))

;; ---------------------------------------------------------------------------
;; Search / Archive Toggle
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/set-environments-search
 (fn [{:keys [db]} [_ text]]
   {:db       (-> db
                  (assoc-in [:environments-page :search] text)
                  (assoc-in [:environments-page :edges] [])
                  (assoc-in [:environments-page :page-info] {:hasNextPage false :endCursor nil}))
    :dispatch [::events/fetch-environments]}))

(rf/reg-event-fx
 ::events/toggle-environments-archived
 (fn [{:keys [db]} _]
   {:db       (-> db
                  (update-in [:environments-page :show-archived] not)
                  (assoc-in [:environments-page :edges] [])
                  (assoc-in [:environments-page :page-info] {:hasNextPage false :endCursor nil}))
    :dispatch [::events/fetch-environments]}))

;; ---------------------------------------------------------------------------
;; Dialog State
;; ---------------------------------------------------------------------------

(rf/reg-event-db
 ::events/open-environment-dialog
 (fn [db [_ environment]]
   (assoc db :environment-dialog
          {:open?       true
           :editing     (some? environment)
           :environment (or environment {:name "" :description ""})})))

(rf/reg-event-db
 ::events/close-environment-dialog
 (fn [db _]
   (assoc db :environment-dialog {:open? false})))

(rf/reg-event-db
 ::events/set-environment-field
 (fn [db [_ field value]]
   (assoc-in db [:environment-dialog :environment field] value)))

;; ---------------------------------------------------------------------------
;; Save (create or update)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/save-environment
 (fn [{:keys [db]} _]
   (let [{:keys [editing environment]} (:environment-dialog db)
         mutation (if editing gql/update-environment-mutation gql/create-environment-mutation)
         input    (if editing
                    (select-keys environment [:id :name :description])
                    (select-keys environment [:name :description]))]
     {:db       (update db :loading conj :save-environment)
      :dispatch [::re-graph/mutate
                 {:query     mutation
                  :variables {:input input}
                  :callback  [::events/on-environment-saved]}]})))

(rf/reg-event-fx
 ::events/on-environment-saved
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (-> db
                (update :loading disj :save-environment)
                (assoc-in [:errors :save-environment] errors))}
       {:db       (-> db
                      (update :loading disj :save-environment)
                      (assoc :environment-dialog {:open? false})
                      (assoc-in [:errors :save-environment] nil))
        :dispatch-n [[::events/fetch-environments]
                     [::events/fetch-environments-list]]}))))

;; ---------------------------------------------------------------------------
;; Archive / Unarchive
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/archive-environment
 (fn [{:keys [db]} [_ id]]
   {:db       (update db :loading conj :archive-environment)
    :dispatch [::re-graph/mutate
               {:query     gql/archive-environment-mutation
                :variables {:id id}
                :callback  [::events/on-environment-archive-toggled]}]}))

(rf/reg-event-fx
 ::events/unarchive-environment
 (fn [{:keys [db]} [_ id]]
   {:db       (update db :loading conj :archive-environment)
    :dispatch [::re-graph/mutate
               {:query     gql/unarchive-environment-mutation
                :variables {:id id}
                :callback  [::events/on-environment-archive-toggled]}]}))

(rf/reg-event-fx
 ::events/on-environment-archive-toggled
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (-> db
                (update :loading disj :archive-environment)
                (assoc-in [:errors :archive-environment] errors))}
       {:db       (-> db
                      (update :loading disj :archive-environment)
                      (assoc :environment-dialog {:open? false}))
        :dispatch-n [[::events/fetch-environments]
                     [::events/fetch-environments-list]]}))))

;; ---------------------------------------------------------------------------
;; Flat list for dropdowns
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-environments-list
 (fn [_ _]
   {:dispatch [::re-graph/query
               {:query     gql/environments-query
                :variables {:first 10}
                :callback  [::events/on-environments-list]}]}))

(rf/reg-event-fx
 ::events/on-environments-list
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data]} response
         nodes (mapv :node (get-in data [:environments :edges]))]
     {:db (assoc db :all-environments nodes)})))

;; ---------------------------------------------------------------------------
;; Search environments for dropdowns
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/search-environments-list
 (fn [_ [_ query]]
   (if (seq query)
     {:dispatch [::re-graph/query
                 {:query     gql/environments-query
                  :variables {:search query :first 10}
                  :callback  [::events/on-environments-search-results]}]}
     {:dispatch [::events/clear-environments-search-results]})))

(rf/reg-event-fx
 ::events/on-environments-search-results
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data]} response
         nodes (mapv :node (get-in data [:environments :edges]))]
     {:db (assoc db :environments-search-results nodes)})))

(rf/reg-event-db
 ::events/clear-environments-search-results
 (fn [db _]
   (assoc db :environments-search-results nil)))
