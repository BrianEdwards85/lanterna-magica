(ns lanterna-magica.events.configurations
  (:require [lanterna-magica.events :as-alias events]
            [lanterna-magica.gql :as gql]
            [re-frame.core :as rf]
            [re-graph.core :as re-graph]))

(def ^:private page-size 30)

;; ---------------------------------------------------------------------------
;; Fetch Configurations (paginated, filtered by service+environment)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-configurations
 (fn [{:keys [db]} _]
   (let [svc-id (get-in db [:configurations-page :filter-service-id])
         env-id (get-in db [:configurations-page :filter-environment-id])]
     {:db       (update db :loading conj :configurations)
      :dispatch [::re-graph/query
                 {:query     gql/configurations-query
                  :variables {:serviceId     svc-id
                              :environmentId env-id
                              :first         page-size}
                  :callback  [::events/on-configurations-fresh]}]})))

(rf/reg-event-fx
 ::events/load-more-configurations
 (fn [{:keys [db]} _]
   (let [svc-id (get-in db [:configurations-page :filter-service-id])
         env-id (get-in db [:configurations-page :filter-environment-id])
         cursor (get-in db [:configurations-page :page-info :endCursor])]
     {:db       (update db :loading conj :configurations)
      :dispatch [::re-graph/query
                 {:query     gql/configurations-query
                  :variables {:serviceId     svc-id
                              :environmentId env-id
                              :first         page-size
                              :after         cursor}
                  :callback  [::events/on-configurations-append]}]})))

(rf/reg-event-fx
 ::events/on-configurations-fresh
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:configurations data)]
     {:db (-> db
              (assoc-in [:configurations-page :edges] (:edges connection))
              (assoc-in [:configurations-page :page-info] (:pageInfo connection))
              (update :loading disj :configurations)
              (assoc-in [:errors :configurations] errors))})))

(rf/reg-event-fx
 ::events/on-configurations-append
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:configurations data)]
     {:db (-> db
              (update-in [:configurations-page :edges] into (:edges connection))
              (assoc-in [:configurations-page :page-info] (:pageInfo connection))
              (update :loading disj :configurations)
              (assoc-in [:errors :configurations] errors))})))

;; ---------------------------------------------------------------------------
;; Filter by service / environment
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/set-config-filter-service
 (fn [{:keys [db]} [_ id]]
   {:db       (-> db
                  (assoc-in [:configurations-page :filter-service-id] (when (seq id) id))
                  (assoc-in [:configurations-page :edges] [])
                  (assoc-in [:configurations-page :page-info] {:hasNextPage false :endCursor nil}))
    :dispatch [::events/fetch-configurations]}))

(rf/reg-event-fx
 ::events/set-config-filter-environment
 (fn [{:keys [db]} [_ id]]
   {:db       (-> db
                  (assoc-in [:configurations-page :filter-environment-id] (when (seq id) id))
                  (assoc-in [:configurations-page :edges] [])
                  (assoc-in [:configurations-page :page-info] {:hasNextPage false :endCursor nil}))
    :dispatch [::events/fetch-configurations]}))

;; ---------------------------------------------------------------------------
;; Create Configuration Dialog
;; ---------------------------------------------------------------------------

(rf/reg-event-db
 ::events/open-configuration-dialog
 (fn [db _]
   (assoc db :configuration-dialog
          {:open?         true
           :configuration {:serviceId     ""
                           :environmentId ""
                           :body-text     "{}"}})))

(rf/reg-event-db
 ::events/close-configuration-dialog
 (fn [db _]
   (assoc db :configuration-dialog {:open? false})))

(rf/reg-event-db
 ::events/set-configuration-field
 (fn [db [_ field value]]
   (assoc-in db [:configuration-dialog :configuration field] value)))

(rf/reg-event-fx
 ::events/save-configuration
 (fn [{:keys [db]} _]
   (let [{:keys [configuration]} (:configuration-dialog db)
         body-text (:body-text configuration)]
     (try
       (let [parsed (.parse js/JSON body-text)
             input  {:serviceId     (:serviceId configuration)
                     :environmentId (:environmentId configuration)
                     :body          parsed}]
         {:db       (update db :loading conj :save-configuration)
          :dispatch [::re-graph/mutate
                     {:query     gql/create-configuration-mutation
                      :variables {:input input}
                      :callback  [::events/on-configuration-saved]}]})
       (catch :default _
         {:db (assoc-in db [:errors :save-configuration]
                        [{:message "Invalid JSON"}])})))))

(rf/reg-event-fx
 ::events/on-configuration-saved
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [errors]} response]
     (if errors
       {:db (-> db
                (update :loading disj :save-configuration)
                (assoc-in [:errors :save-configuration] errors))}
       {:db       (-> db
                      (update :loading disj :save-configuration)
                      (assoc :configuration-dialog {:open? false})
                      (assoc-in [:errors :save-configuration] nil))
        :dispatch [::events/fetch-configurations]}))))

;; ---------------------------------------------------------------------------
;; View single configuration detail
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/select-configuration
 (fn [{:keys [db]} [_ id]]
   (if id
     {:db       (-> db
                    (assoc-in [:configurations-page :selected-id] id)
                    (update :loading conj :configuration-detail))
      :dispatch [::re-graph/query
                 {:query     gql/configuration-query
                  :variables {:id id}
                  :callback  [::events/on-configuration-detail]}]}
     {:db (-> db
              (assoc-in [:configurations-page :selected-id] nil)
              (assoc-in [:configurations-page :selected] nil))})))

(rf/reg-event-fx
 ::events/on-configuration-detail
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response]
     {:db (-> db
              (assoc-in [:configurations-page :selected] (:configuration data))
              (update :loading disj :configuration-detail)
              (assoc-in [:errors :configuration-detail] errors))})))
