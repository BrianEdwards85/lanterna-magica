(ns lanterna-magica.events.configurations
  (:require
   [lanterna-magica.config :as config]
   [lanterna-magica.events :as-alias events]
   [lanterna-magica.events.helpers :as h]
   [lanterna-magica.gql :as gql]
   [re-frame.core :as rf]
   [re-graph.core :as re-graph]))

;; ---------------------------------------------------------------------------
;; Fetch Configurations (paginated, filtered by dimension ids)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/fetch-configurations
  (fn [{:keys [db]} _]
    (let [dim-ids      (get-in db [:configurations-page :filter-dimension-ids])
          current-only (get-in db [:configurations-page :current-only])]
      {:db       (h/start-loading db :configurations)
       :dispatch [::re-graph/query
                  {:query     gql/configurations-query
                   :variables {:dimensionIds (when (seq dim-ids) dim-ids)
                               :currentOnly  (boolean current-only)
                               :first        config/page-size}
                   :callback  [::events/on-configurations-fresh]}]})))

(rf/reg-event-fx
  ::events/load-more-configurations
  (fn [{:keys [db]} _]
    (let [dim-ids      (get-in db [:configurations-page :filter-dimension-ids])
          current-only (get-in db [:configurations-page :current-only])
          cursor       (get-in db [:configurations-page :page-info :endCursor])]
      {:db       (h/start-loading db :configurations)
       :dispatch [::re-graph/query
                  {:query     gql/configurations-query
                   :variables {:dimensionIds (when (seq dim-ids) dim-ids)
                               :currentOnly  (boolean current-only)
                               :first        config/page-size
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
;; Current-Only Toggle
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/toggle-configurations-current-only
  (fn [{:keys [db]} _]
    {:db       (-> db
                   (update-in [:configurations-page :current-only] not)
                   (assoc-in [:configurations-page :edges] [])
                   (assoc-in [:configurations-page :page-info] {:hasNextPage false :endCursor nil}))
     :dispatch [::events/fetch-configurations]}))

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
;; Set / Unset Configuration Current
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/set-configuration-current
  (fn [{:keys [db]} [_ id is-current]]
    {:db       (h/start-loading db :set-configuration-current)
     :dispatch [::re-graph/mutate
                {:query     gql/set-configuration-current-mutation
                 :variables {:id id :isCurrent is-current}
                 :callback  [::events/on-configuration-current-set {:is-current is-current}]}]}))

(rf/reg-event-fx
  ::events/on-configuration-current-set
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [is-current response]}]
    (let [{:keys [errors]} response]
      (if errors
        {:db (h/stop-loading db :set-configuration-current errors)}
        {:db       (h/stop-loading db :set-configuration-current)
         :toast    {:message (if is-current "Configuration made current." "Configuration deactivated.")}
         :dispatch [::events/fetch-configurations]}))))

;; ---------------------------------------------------------------------------
;; Create Configuration Dialog
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/open-configuration-dialog
  (fn [{:keys [db]} [_ {:keys [dimension-ids body-text substitutions]
                        :or   {body-text "{}" substitutions {}}}]]
    (let [dim-ids            (if (seq dimension-ids) dimension-ids (h/base-dimension-ids db))
          pre-populated?     (seq substitutions)
          resolve-dispatches (when pre-populated?
                               (mapv (fn [[path sv-id]]
                                       [::events/resolve-substitution-value path sv-id dim-ids])
                                     substitutions))
          extra-dispatches   (when pre-populated?
                               [[::events/extract-sentinel-paths]])]
      {:db         (assoc db :configuration-dialog
                          {:open?               true
                           :configuration       {:dimensionIds dim-ids :body-text body-text}
                           :sentinel-paths      []
                           :substitutions       substitutions
                           :resolved-values     {}
                           :body-valid?         true
                           :extraction-pending? (boolean pre-populated?)})
       :dispatch-n (-> [[::events/ensure-shared-values-loaded]]
                       (into extra-dispatches)
                       (into resolve-dispatches))})))

(rf/reg-event-db
  ::events/close-configuration-dialog
  (fn [db _]
    (assoc db :configuration-dialog {:open? false})))

(rf/reg-event-fx
  ::events/toggle-configuration-dimension
  (fn [{:keys [db]} [_ dimension-id]]
    (let [path          [:configuration-dialog :configuration :dimensionIds]
          current       (get-in db path [])
          type-id       (h/find-type-id db dimension-id)
          updated       (if (nil? type-id)
                          (conj current dimension-id)
                          (-> (vec (remove #(= (h/find-type-id db %) type-id) current))
                              (conj dimension-id)))
          substitutions (get-in db [:configuration-dialog :substitutions] {})
          re-resolves   (mapv (fn [[jsonpath sv-id]]
                                [::events/resolve-substitution-value jsonpath sv-id updated])
                              (remove (fn [[_ sv-id]] (nil? sv-id)) substitutions))]
      {:db         (-> db
                       (assoc-in path updated)
                       (assoc-in [:configuration-dialog :resolved-values] {}))
       :dispatch-n re-resolves})))

(rf/reg-event-db
  ::events/set-configuration-body
  (fn [db [_ value]]
    (let [valid? (try
                   (js/JSON.parse value)
                   true
                   (catch :default _
                     false))]
      (-> db
          (assoc-in [:configuration-dialog :configuration :body-text] value)
          (assoc-in [:configuration-dialog :body-valid?] valid?)))))

(rf/reg-event-fx
  ::events/extract-sentinel-paths
  (fn [{:keys [db]} _]
    (when (get-in db [:configuration-dialog :body-valid?])
      (let [body-text (get-in db [:configuration-dialog :configuration :body-text])
            parsed    (.parse js/JSON body-text)]
        {:db       (h/start-loading db :extract-sentinel-paths)
         :dispatch [::re-graph/query
                    {:query     gql/extract-sentinel-paths-query
                     :variables {:body parsed}
                     :callback  [::events/on-sentinel-paths-result]}]}))))

(rf/reg-event-fx
  ::events/on-sentinel-paths-result
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response]
      (if errors
        {:db (-> db
                 (assoc-in [:configuration-dialog :extraction-pending?] false)
                 (h/stop-loading :extract-sentinel-paths errors))}
        (let [paths (get data :extractSentinelPaths)]
          {:db (-> db
                   (assoc-in [:configuration-dialog :sentinel-paths] paths)
                   (assoc-in [:configuration-dialog :extraction-pending?] false)
                   (h/stop-loading :extract-sentinel-paths))})))))

(rf/reg-event-fx
  ::events/set-substitution
  (fn [{:keys [db]} [_ jsonpath shared-value-id]]
    (let [dim-ids (get-in db [:configuration-dialog :configuration :dimensionIds])]
      (if shared-value-id
        {:db       (assoc-in db [:configuration-dialog :substitutions jsonpath] shared-value-id)
         :dispatch [::events/resolve-substitution-value jsonpath shared-value-id dim-ids]}
        {:db (-> db
                 (assoc-in [:configuration-dialog :substitutions jsonpath] nil)
                 (update-in [:configuration-dialog :resolved-values] dissoc jsonpath))}))))

(rf/reg-event-fx
  ::events/resolve-substitution-value
  (fn [_ [_ jsonpath shared-value-id dimension-ids]]
    {:dispatch [::re-graph/query
                {:query     gql/resolve-shared-value-query
                 :variables {:sharedValueId shared-value-id
                             :dimensionIds  dimension-ids}
                 :callback  [::events/on-substitution-value-resolved {:jsonpath jsonpath}]}]}))

(rf/reg-event-fx
  ::events/on-substitution-value-resolved
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [jsonpath response]}]
    (let [{:keys [data errors]} response]
      (if errors
        {:db db}
        {:db (assoc-in db [:configuration-dialog :resolved-values jsonpath]
                       (get data :resolveSharedValue))}))))

(rf/reg-event-db
  ::events/set-extraction-pending
  (fn [db [_ pending?]]
    (assoc-in db [:configuration-dialog :extraction-pending?] pending?)))

(rf/reg-event-fx
  ::events/ensure-shared-values-loaded
  (fn [{:keys [db]} _]
    (when (empty? (get-in db [:shared-values-page :edges]))
      {:dispatch [::events/fetch-shared-values]})))

(rf/reg-event-fx
  ::events/save-configuration
  (fn [{:keys [db]} _]
    (let [{:keys [configuration substitutions]} (:configuration-dialog db)
          body-text (:body-text configuration)]
      (try
        (let [parsed        (.parse js/JSON body-text)
              subs-vec      (mapv (fn [[jsonpath sv-id]] {:jsonpath jsonpath :sharedValueId sv-id})
                                  (remove (fn [[_ sv-id]] (nil? sv-id)) substitutions))
              input         {:dimensionIds  (:dimensionIds configuration)
                             :body          parsed
                             :substitutions subs-vec}]
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
         :toast    {:message "Configuration created."}
         :dispatch [::events/fetch-configurations]}))))

;; ---------------------------------------------------------------------------
;; View single configuration detail
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/load-configuration
  (fn [{:keys [db]} [_ id]]
    {:db       (-> db
                   (assoc-in [:configurations-page :selected-id] id)
                   (h/start-loading :configuration-detail))
     :dispatch [::re-graph/query
                {:query     gql/configuration-query
                 :variables {:ids [id]}
                 :callback  [::events/on-configuration-detail]}]}))

(rf/reg-event-db
  ::events/deselect-configuration
  (fn [db _]
    (-> db
        (assoc-in [:configurations-page :selected-id] nil)
        (assoc-in [:configurations-page :selected] nil))))

(rf/reg-event-fx
  ::events/select-configuration
  (fn [{:keys [db]} [_ id]]
    (if id
      {:db       (-> db
                     (assoc-in [:configurations-page :selected-id] id))
       :navigate [:route/configuration {:id id}]}
      {:db       (-> db
                     (assoc-in [:configurations-page :selected-id] nil)
                     (assoc-in [:configurations-page :selected] nil))
       :navigate :route/configurations})))

(rf/reg-event-fx
  ::events/on-configuration-detail
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          configuration (first (:configurationsByIds data))]
      (if (and (nil? configuration) (nil? errors))
        {:db       (-> db
                       (assoc-in [:configurations-page :selected-id] nil)
                       (assoc-in [:configurations-page :selected] nil)
                       (h/stop-loading :configuration-detail))
         :navigate :route/configurations}
        {:db (-> db
                 (assoc-in [:configurations-page :selected] configuration)
                 (h/stop-loading :configuration-detail errors))}))))
