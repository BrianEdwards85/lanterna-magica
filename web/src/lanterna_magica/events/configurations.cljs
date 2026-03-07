(ns lanterna-magica.events.configurations
  (:require [lanterna-magica.events :as-alias events]
            [lanterna-magica.events.helpers :as h]
            [lanterna-magica.gql :as gql]
            [re-frame.core :as rf]
            [re-graph.core :as re-graph]))

(def ^:private page-size 30)

;; ---------------------------------------------------------------------------
;; Fetch Configurations (paginated, filtered by dimension ids)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/fetch-configurations
 (fn [{:keys [db]} _]
   (let [dim-ids (get-in db [:configurations-page :filter-dimension-ids])]
     {:db       (h/start-loading db :configurations)
      :dispatch [::re-graph/query
                 {:query     gql/configurations-query
                  :variables {:dimensionIds (when (seq dim-ids) dim-ids)
                              :first        page-size}
                  :callback  [::events/on-configurations-fresh]}]})))

(rf/reg-event-fx
 ::events/load-more-configurations
 (fn [{:keys [db]} _]
   (let [dim-ids (get-in db [:configurations-page :filter-dimension-ids])
         cursor  (get-in db [:configurations-page :page-info :endCursor])]
     {:db       (h/start-loading db :configurations)
      :dispatch [::re-graph/query
                 {:query     gql/configurations-query
                  :variables {:dimensionIds (when (seq dim-ids) dim-ids)
                              :first        page-size
                              :after        cursor}
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
              (h/stop-loading :configurations errors))})))

(rf/reg-event-fx
 ::events/on-configurations-append
 [rf/unwrap]
 (fn [{:keys [db]} {:keys [response]}]
   (let [{:keys [data errors]} response
         connection (:configurations data)]
     {:db (-> db
              (update-in [:configurations-page :edges] into (:edges connection))
              (assoc-in [:configurations-page :page-info] (:pageInfo connection))
              (h/stop-loading :configurations errors))})))

;; ---------------------------------------------------------------------------
;; Filter by dimension ids
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
 ::events/set-config-filter-dimension
 (fn [{:keys [db]} [_ dimension-id]]
   (let [current (get-in db [:configurations-page :filter-dimension-ids] [])
         updated (if (some #{dimension-id} current)
                   (vec (remove #{dimension-id} current))
                   (conj current dimension-id))]
     {:db       (-> db
                    (assoc-in [:configurations-page :filter-dimension-ids] updated)
                    (assoc-in [:configurations-page :edges] [])
                    (assoc-in [:configurations-page :page-info] {:hasNextPage false :endCursor nil}))
      :dispatch [::events/fetch-configurations]})))

(rf/reg-event-fx
 ::events/clear-config-filters
 (fn [{:keys [db]} _]
   {:db       (-> db
                  (assoc-in [:configurations-page :filter-dimension-ids] [])
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
           :configuration {:dimensionIds []
                           :body-text    "{}"}})))

(rf/reg-event-db
 ::events/close-configuration-dialog
 (fn [db _]
   (assoc db :configuration-dialog {:open? false})))

(rf/reg-event-db
 ::events/set-configuration-field
 (fn [db [_ field value]]
   (assoc-in db [:configuration-dialog :configuration field] value)))

(rf/reg-event-db
 ::events/toggle-configuration-dimension
 (fn [db [_ dimension-id]]
   (let [path    [:configuration-dialog :configuration :dimensionIds]
         current (get-in db path [])
         updated (if (some #{dimension-id} current)
                   (vec (remove #{dimension-id} current))
                   (conj current dimension-id))]
     (assoc-in db path updated))))

(rf/reg-event-fx
 ::events/save-configuration
 (fn [{:keys [db]} _]
   (let [{:keys [configuration]} (:configuration-dialog db)
         body-text (:body-text configuration)]
     (try
       (let [parsed (.parse js/JSON body-text)
             input  {:dimensionIds (:dimensionIds configuration)
                     :body         parsed}]
         {:db       (h/start-loading db :save-configuration)
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
       {:db (h/stop-loading db :save-configuration errors)}
       {:db       (-> db
                      (h/stop-loading :save-configuration)
                      (assoc :configuration-dialog {:open? false}))
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
                    (h/start-loading :configuration-detail))
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
              (h/stop-loading :configuration-detail errors))})))
