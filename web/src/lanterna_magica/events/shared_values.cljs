(ns lanterna-magica.events.shared-values
  (:require
   [lanterna-magica.config :as config]
   [lanterna-magica.events :as-alias events]
   [lanterna-magica.events.helpers :as h]
   [lanterna-magica.gql :as gql]
   [re-frame.core :as rf]
   [re-graph.core :as re-graph]))

;; ---------------------------------------------------------------------------
;; Fetch Shared Values (paginated list)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/fetch-shared-values
  (fn [{:keys [db]} _]
    (let [archived (get-in db [:shared-values-page :show-archived])
          search   (get-in db [:shared-values-page :search])]
      {:db       (h/start-loading db :shared-values)
       :dispatch [::re-graph/query
                  {:query     gql/shared-values-query
                   :variables {:includeArchived (boolean archived)
                               :search          (when (seq search) search)
                               :first           config/page-size}
                   :callback  [::events/on-shared-values-fresh]}]})))

(rf/reg-event-fx
  ::events/load-more-shared-values
  (fn [{:keys [db]} _]
    (let [archived (get-in db [:shared-values-page :show-archived])
          search   (get-in db [:shared-values-page :search])
          cursor   (get-in db [:shared-values-page :page-info :endCursor])]
      {:db       (h/start-loading db :shared-values)
       :dispatch [::re-graph/query
                  {:query     gql/shared-values-query
                   :variables {:includeArchived (boolean archived)
                               :search          (when (seq search) search)
                               :first           config/page-size
                               :after           cursor}
                   :callback  [::events/on-shared-values-append]}]})))

(rf/reg-event-fx
  ::events/on-shared-values-fresh
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          connection (:sharedValues data)]
      {:db (-> db
               (assoc-in [:shared-values-page :edges] (:edges connection))
               (assoc-in [:shared-values-page :page-info] (:pageInfo connection))
               (h/stop-loading :shared-values errors))})))

(rf/reg-event-fx
  ::events/on-shared-values-append
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          connection (:sharedValues data)]
      {:db (-> db
               (update-in [:shared-values-page :edges] into (:edges connection))
               (assoc-in [:shared-values-page :page-info] (:pageInfo connection))
               (h/stop-loading :shared-values errors))})))

;; ---------------------------------------------------------------------------
;; Search + Archive Toggle
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/set-shared-values-search
  (fn [{:keys [db]} [_ text]]
    {:db       (-> db
                   (assoc-in [:shared-values-page :search] text)
                   (assoc-in [:shared-values-page :edges] [])
                   (assoc-in [:shared-values-page :page-info] {:hasNextPage false :endCursor nil}))
     :dispatch [::events/fetch-shared-values]}))

(rf/reg-event-fx
  ::events/toggle-shared-values-archived
  (fn [{:keys [db]} _]
    {:db       (-> db
                   (update-in [:shared-values-page :show-archived] not)
                   (assoc-in [:shared-values-page :edges] [])
                   (assoc-in [:shared-values-page :page-info] {:hasNextPage false :endCursor nil}))
     :dispatch [::events/fetch-shared-values]}))

;; ---------------------------------------------------------------------------
;; Current-Only Toggle (Revisions)
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/toggle-revisions-current-only
  (fn [{:keys [db]} _]
    (let [sv-id (get-in db [:shared-values-page :selected-id])]
      {:db       (-> db
                     (update-in [:shared-values-page :current-only] not)
                     (assoc-in [:shared-values-page :revisions] {:edges []})
                     (assoc-in [:shared-values-page :revisions-page-info] nil))
       :dispatch [::events/fetch-revisions sv-id]})))

;; ---------------------------------------------------------------------------
;; Select Shared Value + Load Revisions
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/select-shared-value
  (fn [{:keys [db]} [_ id]]
    (if id
      {:db       (-> db
                     (assoc-in [:shared-values-page :selected-id] id)
                     (assoc-in [:shared-values-page :revisions] {:edges []})
                     (assoc-in [:shared-values-page :revisions-page-info] nil))
       :dispatch [::events/fetch-revisions id]}
      {:db (-> db
               (assoc-in [:shared-values-page :selected-id] nil)
               (assoc-in [:shared-values-page :revisions] {:edges []})
               (assoc-in [:shared-values-page :revisions-page-info] nil))})))

(rf/reg-event-fx
  ::events/fetch-revisions
  (fn [{:keys [db]} [_ shared-value-id]]
    (let [current-only (get-in db [:shared-values-page :current-only])]
      {:db       (h/start-loading db :revisions)
       :dispatch [::re-graph/query
                  {:query     gql/shared-value-query
                   :variables {:id          shared-value-id
                               :currentOnly (boolean current-only)
                               :first       config/page-size}
                   :callback  [::events/on-revisions-fresh]}]})))

(rf/reg-event-fx
  ::events/on-revisions-fresh
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          connection (get-in data [:sharedValue :revisions])]
      {:db (-> db
               (assoc-in [:shared-values-page :revisions] {:edges (:edges connection)})
               (assoc-in [:shared-values-page :revisions-page-info] (:pageInfo connection))
               (h/stop-loading :revisions errors))})))

;; ---------------------------------------------------------------------------
;; Load More Revisions
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/load-more-revisions
  (fn [{:keys [db]} _]
    (let [sv-id        (get-in db [:shared-values-page :selected-id])
          current-only (get-in db [:shared-values-page :current-only])
          cursor       (get-in db [:shared-values-page :revisions-page-info :endCursor])]
      {:db       (h/start-loading db :revisions)
       :dispatch [::re-graph/query
                  {:query     gql/shared-value-query
                   :variables {:id          sv-id
                               :currentOnly (boolean current-only)
                               :first       config/page-size
                               :after       cursor}
                   :callback  [::events/on-revisions-append]}]})))

(rf/reg-event-fx
  ::events/on-revisions-append
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [data errors]} response
          connection (get-in data [:sharedValue :revisions])]
      {:db (-> db
               (update-in [:shared-values-page :revisions :edges] into (:edges connection))
               (assoc-in [:shared-values-page :revisions-page-info] (:pageInfo connection))
               (h/stop-loading :revisions errors))})))

;; ---------------------------------------------------------------------------
;; Create Shared Value Dialog
;; ---------------------------------------------------------------------------

(rf/reg-event-db
  ::events/open-shared-value-dialog
  (fn [db [_ shared-value]]
    (assoc db :shared-value-dialog
           {:open?        true
            :editing      (some? shared-value)
            :shared-value (or shared-value {:name ""})})))

(rf/reg-event-db
  ::events/close-shared-value-dialog
  (fn [db _]
    (assoc db :shared-value-dialog {:open? false})))

(rf/reg-event-db
  ::events/set-shared-value-field
  (fn [db [_ field value]]
    (assoc-in db [:shared-value-dialog :shared-value field] value)))

(rf/reg-event-fx
  ::events/save-shared-value
  (fn [{:keys [db]} _]
    (let [{:keys [editing shared-value]} (:shared-value-dialog db)
          mutation (if editing
                     gql/update-shared-value-mutation
                     gql/create-shared-value-mutation)
          input    (if editing
                     (select-keys shared-value [:id :name])
                     (select-keys shared-value [:name]))]
      {:db       (h/start-loading db :save-shared-value)
       :dispatch [::re-graph/mutate
                  {:query     mutation
                   :variables {:input input}
                   :callback  [::events/on-shared-value-saved]}]})))

(rf/reg-event-fx
  ::events/on-shared-value-saved
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [errors]} response]
      (if errors
        {:db (h/stop-loading db :save-shared-value errors)}
        {:db       (-> db
                       (h/stop-loading :save-shared-value)
                       (assoc :shared-value-dialog {:open? false}))
         :dispatch [::events/fetch-shared-values]}))))

;; ---------------------------------------------------------------------------
;; Archive / Unarchive
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/archive-shared-value
  (fn [{:keys [db]} [_ id]]
    {:db       (h/start-loading db :archive-shared-value)
     :dispatch [::re-graph/mutate
                {:query     gql/archive-shared-value-mutation
                 :variables {:id id}
                 :callback  [::events/on-shared-value-archive-toggled]}]}))

(rf/reg-event-fx
  ::events/unarchive-shared-value
  (fn [{:keys [db]} [_ id]]
    {:db       (h/start-loading db :archive-shared-value)
     :dispatch [::re-graph/mutate
                {:query     gql/unarchive-shared-value-mutation
                 :variables {:id id}
                 :callback  [::events/on-shared-value-archive-toggled]}]}))

(rf/reg-event-fx
  ::events/on-shared-value-archive-toggled
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [errors]} response]
      (if errors
        {:db (h/stop-loading db :archive-shared-value errors)}
        {:db       (-> db
                       (h/stop-loading :archive-shared-value)
                       (assoc :shared-value-dialog {:open? false}))
         :dispatch [::events/fetch-shared-values]}))))

;; ---------------------------------------------------------------------------
;; Set / Unset Revision Current
;; ---------------------------------------------------------------------------

(rf/reg-event-fx
  ::events/set-revision-current
  (fn [{:keys [db]} [_ id is-current]]
    {:db       (h/start-loading db :set-revision-current)
     :dispatch [::re-graph/mutate
                {:query     gql/set-revision-current-mutation
                 :variables {:id id :isCurrent is-current}
                 :callback  [::events/on-revision-current-set]}]}))

(rf/reg-event-fx
  ::events/on-revision-current-set
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [errors]} response
          sv-id (get-in db [:shared-values-page :selected-id])]
      (if errors
        {:db (h/stop-loading db :set-revision-current errors)}
        {:db       (h/stop-loading db :set-revision-current)
         :dispatch [::events/fetch-revisions sv-id]}))))

;; ---------------------------------------------------------------------------
;; Create Revision Dialog
;; ---------------------------------------------------------------------------

(rf/reg-event-db
  ::events/open-revision-dialog
  (fn [db [_ shared-value-id]]
    (assoc db :revision-dialog
           {:open?    true
            :revision {:sharedValueId  shared-value-id
                       :dimensionIds   []
                       :value-text     ""}})))

(rf/reg-event-db
  ::events/close-revision-dialog
  (fn [db _]
    (assoc db :revision-dialog {:open? false})))

(rf/reg-event-db
  ::events/set-revision-field
  (fn [db [_ field value]]
    (assoc-in db [:revision-dialog :revision field] value)))

(rf/reg-event-db
  ::events/toggle-revision-dimension
  (fn [db [_ dimension-id]]
    (let [path    [:revision-dialog :revision :dimensionIds]
          current (get-in db path [])
          updated (if (some #{dimension-id} current)
                    (vec (remove #{dimension-id} current))
                    (conj current dimension-id))]
      (assoc-in db path updated))))

(rf/reg-event-fx
  ::events/save-revision
  (fn [{:keys [db]} _]
    (let [{:keys [revision]} (:revision-dialog db)
          value-text (:value-text revision)]
      (try
        (let [parsed (.parse js/JSON value-text)
              input  {:sharedValueId (:sharedValueId revision)
                      :dimensionIds  (:dimensionIds revision)
                      :value         parsed}]
          {:db       (h/start-loading db :save-revision)
           :dispatch [::re-graph/mutate
                      {:query     gql/create-shared-value-revision-mutation
                       :variables {:input input}
                       :callback  [::events/on-revision-saved]}]})
        (catch :default _
          {:db (assoc-in db [:errors :save-revision]
                         [{:message "Invalid JSON"}])})))))

(rf/reg-event-fx
  ::events/on-revision-saved
  [rf/unwrap]
  (fn [{:keys [db]} {:keys [response]}]
    (let [{:keys [errors]} response
          sv-id (get-in db [:revision-dialog :revision :sharedValueId])]
      (if errors
        {:db (h/stop-loading db :save-revision errors)}
        {:db       (-> db
                       (h/stop-loading :save-revision)
                       (assoc :revision-dialog {:open? false}))
         :dispatch [::events/fetch-revisions sv-id]}))))
