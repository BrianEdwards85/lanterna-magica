(ns lanterna-magica.events.services
  (:require [lanterna-magica.events :as-alias events]
            [lanterna-magica.gql :as gql]
            [re-frame.core :as rf]
            [re-graph.core :as re-graph]))

(def ^:private page-size 30)

;; ---------------------------------------------------------------------------
;; Fetch Services (paginated list)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-services
 (fn [{:keys [db]} _]
   (let [search   (get-in db [:services-page :search])
         archived (get-in db [:services-page :show-archived])]
     {:db       (update db :loading conj :services)
      :dispatch [::re-graph/query
                 {:query     gql/services-query
                  :variables {:search          (when (seq search) search)
                              :includeArchived (boolean archived)
                              :first           page-size}
                  :callback  [::events/on-services-fresh]}]})))

(rf/reg-event-fx
 ::events/load-more-services
 (fn [{:keys [db]} _]
   (let [search   (get-in db [:services-page :search])
         archived (get-in db [:services-page :show-archived])
         cursor   (get-in db [:services-page :page-info :endCursor])]
     {:db       (update db :loading conj :services)
      :dispatch [::re-graph/query
                 {:query     gql/services-query
                  :variables {:search          (when (seq search) search)
                              :includeArchived (boolean archived)
                              :first           page-size
                              :after           cursor}
                  :callback  [::events/on-services-append]}]})))

(rf/reg-event-fx
 ::events/on-services-fresh
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:services data)]
     {:db (-> db
              (assoc-in [:services-page :edges] (:edges connection))
              (assoc-in [:services-page :page-info] (:pageInfo connection))
              (update :loading disj :services)
              (assoc-in [:errors :services] errors))})))

(rf/reg-event-fx
 ::events/on-services-append
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:services data)]
     {:db (-> db
              (update-in [:services-page :edges] into (:edges connection))
              (assoc-in [:services-page :page-info] (:pageInfo connection))
              (update :loading disj :services)
              (assoc-in [:errors :services] errors))})))

;; ---------------------------------------------------------------------------
;; Search / Archive Toggle
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/set-services-search
 (fn [{:keys [db]} [_ text]]
   {:db       (-> db
                  (assoc-in [:services-page :search] text)
                  (assoc-in [:services-page :edges] [])
                  (assoc-in [:services-page :page-info] {:hasNextPage false :endCursor nil}))
    :dispatch [::events/fetch-services]}))

(rf/reg-event-fx
 ::events/toggle-services-archived
 (fn [{:keys [db]} _]
   {:db       (-> db
                  (update-in [:services-page :show-archived] not)
                  (assoc-in [:services-page :edges] [])
                  (assoc-in [:services-page :page-info] {:hasNextPage false :endCursor nil}))
    :dispatch [::events/fetch-services]}))

;; ---------------------------------------------------------------------------
;; Dialog State
;; ---------------------------------------------------------------------------

(rf/reg-event-db
 ::events/open-service-dialog
 (fn [db [_ service]]
   (assoc db :service-dialog
          {:open?   true
           :editing (some? service)
           :service (or service {:name "" :description ""})})))

(rf/reg-event-db
 ::events/close-service-dialog
 (fn [db _]
   (assoc db :service-dialog {:open? false})))

(rf/reg-event-db
 ::events/set-service-field
 (fn [db [_ field value]]
   (assoc-in db [:service-dialog :service field] value)))

;; ---------------------------------------------------------------------------
;; Save (create or update)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/save-service
 (fn [{:keys [db]} _]
   (let [{:keys [editing service]} (:service-dialog db)
         mutation (if editing gql/update-service-mutation gql/create-service-mutation)
         input    (if editing
                    (select-keys service [:id :name :description])
                    (select-keys service [:name :description]))]
     {:db       (update db :loading conj :save-service)
      :dispatch [::re-graph/mutate
                 {:query     mutation
                  :variables {:input input}
                  :callback  [::events/on-service-saved]}]})))

(rf/reg-event-fx
 ::events/on-service-saved
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (-> db
                (update :loading disj :save-service)
                (assoc-in [:errors :save-service] errors))}
       {:db       (-> db
                      (update :loading disj :save-service)
                      (assoc :service-dialog {:open? false})
                      (assoc-in [:errors :save-service] nil))
        :dispatch-n [[::events/fetch-services]
                     [::events/fetch-services-list]]}))))

;; ---------------------------------------------------------------------------
;; Archive / Unarchive
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/archive-service
 (fn [{:keys [db]} [_ id]]
   {:db       (update db :loading conj :archive-service)
    :dispatch [::re-graph/mutate
               {:query     gql/archive-service-mutation
                :variables {:id id}
                :callback  [::events/on-service-archive-toggled]}]}))

(rf/reg-event-fx
 ::events/unarchive-service
 (fn [{:keys [db]} [_ id]]
   {:db       (update db :loading conj :archive-service)
    :dispatch [::re-graph/mutate
               {:query     gql/unarchive-service-mutation
                :variables {:id id}
                :callback  [::events/on-service-archive-toggled]}]}))

(rf/reg-event-fx
 ::events/on-service-archive-toggled
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (-> db
                (update :loading disj :archive-service)
                (assoc-in [:errors :archive-service] errors))}
       {:db       (-> db
                      (update :loading disj :archive-service)
                      (assoc :service-dialog {:open? false}))
        :dispatch-n [[::events/fetch-services]
                     [::events/fetch-services-list]]}))))

;; ---------------------------------------------------------------------------
;; Flat list for dropdowns
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-services-list
 (fn [_ _]
   {:dispatch [::re-graph/query
               {:query     gql/services-query
                :variables {:first 10}
                :callback  [::events/on-services-list]}]}))

(rf/reg-event-fx
 ::events/on-services-list
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data]} response
         nodes (mapv :node (get-in data [:services :edges]))]
     {:db (assoc db :all-services nodes)})))

;; ---------------------------------------------------------------------------
;; Search services for dropdowns
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/search-services-list
 (fn [_ [_ query]]
   (if (seq query)
     {:dispatch [::re-graph/query
                 {:query     gql/services-query
                  :variables {:search query :first 10}
                  :callback  [::events/on-services-search-results]}]}
     {:dispatch [::events/clear-services-search-results]})))

(rf/reg-event-fx
 ::events/on-services-search-results
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data]} response
         nodes (mapv :node (get-in data [:services :edges]))]
     {:db (assoc db :services-search-results nodes)})))

(rf/reg-event-db
 ::events/clear-services-search-results
 (fn [db _]
   (assoc db :services-search-results nil)))
