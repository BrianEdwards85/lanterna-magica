(ns lanterna-magica.events.outputs
  (:require
   [lanterna-magica.config :as config]
   [lanterna-magica.events :as-alias events]
   [lanterna-magica.events.helpers :as h]
   [lanterna-magica.gql :as gql]
   [re-frame.core :as rf]
   [re-graph.core :as re-graph]))

;; ---------------------------------------------------------------------------
;; Fetch Outputs (paginated)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/fetch-outputs
  (fn [{:keys [db]} _]
    (let [archived (get-in db [:outputs-page :show-archived])]
      {:db       (h/start-loading db :outputs)
       :dispatch [::re-graph/query
                  {:query     gql/outputs-query
                   :variables {:includeArchived (boolean archived)
                               :first           config/page-size}
                   :callback  [::events/on-outputs-fresh]}]})))

(rf/reg-event-fx
  ::events/load-more-outputs
  (fn [{:keys [db]} _]
    (let [archived (get-in db [:outputs-page :show-archived])
          cursor   (get-in db [:outputs-page :page-info :endCursor])]
      {:db       (h/start-loading db :outputs)
       :dispatch [::re-graph/query
                  {:query     gql/outputs-query
                   :variables {:includeArchived (boolean archived)
                               :first           config/page-size
                               :after           cursor}
                   :callback  [::events/on-outputs-append]}]})))

(rf/reg-event-fx
  ::events/on-outputs-fresh
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          connection (:outputs data)]
      {:db (-> db
               (assoc-in [:outputs-page :edges] (:edges connection))
               (assoc-in [:outputs-page :page-info] (:pageInfo connection))
               (h/stop-loading :outputs errors))})))

(rf/reg-event-fx
  ::events/on-outputs-append
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          connection (:outputs data)]
      {:db (-> db
               (update-in [:outputs-page :edges] into (:edges connection))
               (assoc-in [:outputs-page :page-info] (:pageInfo connection))
               (h/stop-loading :outputs errors))})))

;; ---------------------------------------------------------------------------
;; Output Dialog
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/open-output-dialog
  (fn [{:keys [db]} _]
    {:db (assoc db :output-dialog {:open? true :output {:format "json"}})}))

(rf/reg-event-fx
  ::events/close-output-dialog
  (fn [{:keys [db]} _]
    {:db (assoc db :output-dialog {:open? false :output nil})}))

(rf/reg-event-db
  ::events/set-output-field
  (fn [db [_ field value]]
    (assoc-in db [:output-dialog :output field] value)))

(rf/reg-event-db
  ::events/toggle-output-dimension
  (fn [db [_ dimension-id]]
    (let [path    [:output-dialog :output :dimensionIds]
          current (get-in db path [])
          updated (if (some #{dimension-id} current)
                    (vec (remove #{dimension-id} current))
                    (conj current dimension-id))]
      (assoc-in db path updated))))

;; ---------------------------------------------------------------------------
;; Save / Archive Output
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/save-output
  (fn [{:keys [db]} _]
    (let [output (:output (:output-dialog db))
          input  (select-keys output [:pathTemplate :format :dimensionIds])]
      {:db       (h/start-loading db :save-output)
       :dispatch [::re-graph/mutate
                  {:query     gql/create-output-mutation
                   :variables {:input input}
                   :callback  [::events/on-output-saved]}]})))

(rf/reg-event-fx
  ::events/on-output-saved
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [errors]} response]
      (if errors
        {:db (h/stop-loading db :save-output errors)}
        {:db       (-> db
                       (h/stop-loading :save-output)
                       (assoc :output-dialog {:open? false :output nil}))
         :toast    {:message "Output created."}
         :dispatch [::events/fetch-outputs]}))))

(rf/reg-event-fx
  ::events/archive-output
  (fn [{:keys [db]} [_ id]]
    {:db       (h/start-loading db :archive-output)
     :dispatch [::re-graph/mutate
                {:query     gql/archive-output-mutation
                 :variables {:id id}
                 :callback  [::events/on-output-archived]}]}))

(rf/reg-event-fx
  ::events/on-output-archived
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [errors]} response]
      (if errors
        {:db (h/stop-loading db :archive-output errors)}
        {:db       (-> db
                       (h/stop-loading :archive-output)
                       (assoc :output-dialog {:open? false :output nil}))
         :toast    {:message "Output archived."}
         :dispatch [::events/fetch-outputs]}))))

;; ---------------------------------------------------------------------------
;; Trigger Output
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/trigger-output
  (fn [{:keys [db]} [_ id]]
    {:db       (h/start-loading db [:trigger-output id])
     :dispatch [::re-graph/mutate
                {:query     gql/trigger-output-mutation
                 :variables {:id id}
                 :callback  [::events/on-output-triggered {:id id}]}]}))

(rf/reg-event-fx
  ::events/on-output-triggered
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [id response]}]
    (let [{:keys [errors]} response]
      (if errors
        {:db (h/stop-loading db [:trigger-output id] errors)}
        {:db         (h/stop-loading db [:trigger-output id])
         :toast      {:message "Output triggered."}
         :dispatch-n [[::events/load-output id]
                      [::events/fetch-outputs]]}))))

;; ---------------------------------------------------------------------------
;; Select / Deselect Output
;; ---------------------------------------------------------------------------

(rf/reg-event-db
  ::events/deselect-output
  (fn [db _]
    (-> db
        (assoc-in [:outputs-page :selected-id] nil)
        (assoc-in [:outputs-page :selected] nil))))

;; ---------------------------------------------------------------------------
;; Load Single Output
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/load-output
  (fn [{:keys [db]} [_ id]]
    {:db       (-> db
                   (assoc-in [:outputs-page :selected-id] id)
                   (h/start-loading :output-detail))
     :dispatch [::re-graph/query
                {:query     gql/output-query
                 :variables {:ids [id]}
                 :callback  [::events/on-output-detail]}]}))

(rf/reg-event-fx
  ::events/on-output-detail
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          output (first (:outputsByIds data))]
      (if (and (nil? output) (nil? errors))
        {:db       (-> db
                       (assoc-in [:outputs-page :selected-id] nil)
                       (assoc-in [:outputs-page :selected] nil)
                       (h/stop-loading :output-detail))
         :navigate :route/outputs}
        {:db (-> db
                 (assoc-in [:outputs-page :selected] output)
                 (h/stop-loading :output-detail errors))}))))
