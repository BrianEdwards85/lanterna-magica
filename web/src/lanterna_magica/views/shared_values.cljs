(ns lanterna-magica.views.shared-values
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.components.archived-banner :as archived-banner]
   [lanterna-magica.components.current-status :as current-status]
   [lanterna-magica.components.dimension-picker :as dim-picker]
   [lanterna-magica.components.dimensions-label :as dimensions-label]
   [lanterna-magica.components.error-banner :as error-banner]
   [lanterna-magica.components.inputs :as inputs]
   [lanterna-magica.components.json-block :as json-block]
   [lanterna-magica.components.load-more :as load-more]
   [lanterna-magica.components.search-bar :as search-bar]
   [lanterna-magica.components.states :as states]
   [lanterna-magica.events :as events]
   [lanterna-magica.subs :as subs]
   [re-frame.core :as rf]
   [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create Shared Value Dialog
;; ---------------------------------------------------------------------------

(defn shared-value-dialog []
  (let [{:keys [open? editing shared-value]} @(rf/subscribe [::subs/shared-value-dialog])
        saving?    @(rf/subscribe [::subs/loading? :save-shared-value])
        archiving? @(rf/subscribe [::subs/loading? :archive-shared-value])
        error      @(rf/subscribe [::subs/error :save-shared-value])]
    (when open?
      (let [archived? (some? (:archivedAt shared-value))]
        [bp/dialog {:title    (if editing "Edit Shared Value" "Create Shared Value")
                    :icon     "variable"
                    :is-open  true
                    :on-close #(rf/dispatch [::events/close-shared-value-dialog])
                    :class    "w-full max-w-md"}
         [bp/dialog-body
          (when (and editing archived?)
            [archived-banner/archived-banner "This shared value is archived."])
          [:div.mb-4
           [:label.bp6-label "Name"]
           [inputs/local-input {:value       (or (:name shared-value) "")
                                :placeholder "DATABASE_URL"
                                :disabled    (and editing archived?)
                                :on-change   #(rf/dispatch [::events/set-shared-value-field :name %])}]]
          (when error
            [error-banner/error-banner "Failed to save shared value." error])
          (when editing
            [:div {:class "mt-6 pt-4 border-t border-tn-border"}
             (if archived?
               [bp/button {:icon "undo" :text "Unarchive" :intent "success" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/unarchive-shared-value (:id shared-value)])}]
               [bp/button {:icon "trash" :text "Archive" :intent "danger" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/archive-shared-value (:id shared-value)])}])])]
         [bp/dialog-footer
          {:actions
           (r/as-element
             [:<>
              [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-shared-value-dialog])}]
              (when-not archived?
                [bp/button {:text "Save" :intent "primary" :icon "tick"
                            :loading saving?
                            :on-click #(rf/dispatch [::events/save-shared-value])}])])}]]))))

;; ---------------------------------------------------------------------------
;; Create Revision Dialog
;; ---------------------------------------------------------------------------

(defn revision-dialog []
  (let [{:keys [open? revision]} @(rf/subscribe [::subs/revision-dialog])
        saving?      @(rf/subscribe [::subs/loading? :save-revision])
        error        @(rf/subscribe [::subs/error :save-revision])]
    (when open?
      [bp/dialog {:title    "Create Revision"
                  :icon     "history"
                  :is-open  true
                  :on-close #(rf/dispatch [::events/close-revision-dialog])
                  :class    "w-full max-w-md"}
       [bp/dialog-body
        [dim-picker/dimension-picker
         {:selected-ids (or (:dimensionIds revision) [])
          :on-toggle    #(rf/dispatch [::events/toggle-revision-dimension %])
          :on-clear     #(rf/dispatch [::events/toggle-revision-dimension %])}]
        [:div.mb-4
         [:label.bp6-label "Value (JSON)"]
         [inputs/local-textarea {:rows        6
                                 :value       (or (:value-text revision) "")
                                 :placeholder "{\"key\": \"value\"}"
                                 :class       "font-mono text-sm"
                                 :on-change   #(rf/dispatch [::events/set-revision-field :value-text %])}]]
        (when error
          [error-banner/error-banner "Failed to create revision." error])]
       [bp/dialog-footer
        {:actions
         (r/as-element
           [:<>
            [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-revision-dialog])}]
            [bp/button {:text "Create" :intent "primary" :icon "tick"
                        :loading  saving?
                        :on-click #(rf/dispatch [::events/save-revision])}]])}]])))

;; ---------------------------------------------------------------------------
;; Left sidebar -- shared values list
;; ---------------------------------------------------------------------------

(defn- shared-values-sidebar []
  (let [{:keys [search show-archived edges page-info selected-id]} @(rf/subscribe [::subs/shared-values-page])
        loading?   @(rf/subscribe [::subs/loading? :shared-values])
        page-error @(rf/subscribe [::subs/error :shared-values])]
    [:div {:class "w-56 shrink-0 border-r border-tn-border pr-3"}
     [:div.flex.items-center.justify-between.mb-3
      [:span.font-semibold.text-sm.text-tn-fg-muted "Shared Values"]
      [:div.flex.items-center.gap-1
       [bp/button {:icon     "plus"
                   :minimal  true
                   :small    true
                   :on-click #(rf/dispatch [::events/open-shared-value-dialog])}]
       [bp/button {:icon     "refresh"
                   :minimal  true
                   :small    true
                   :loading  loading?
                   :on-click #(rf/dispatch [::events/fetch-shared-values])}]]]
     [search-bar/search-bar {:search             (or search "")
                             :on-search-change   #(rf/dispatch [::events/set-shared-values-search %])
                             :show-archived      show-archived
                             :on-toggle-archived #(rf/dispatch [::events/toggle-shared-values-archived])
                             :placeholder        "Search shared values..."}]
     (when page-error
       [error-banner/error-banner "Failed to load shared values." page-error])
     (cond
       (and loading? (empty? edges))
       [states/loading-spinner]

       (empty? edges)
       [:div.text-sm.text-tn-fg-dim.p-2
        (if (seq search)
          "No results."
          "No shared values yet.")]

       :else
       [:div {:class "flex flex-col gap-1"}
        (for [edge edges]
          (let [node (:node edge)
                selected? (= (:id node) selected-id)]
            ^{:key (:id node)}
            [:div {:class    (str "px-3 py-2 rounded cursor-pointer transition-all flex items-center justify-between "
                                  (if selected?
                                    "bg-tn-selection ring-1 ring-tn-blue/50"
                                    "hover:brightness-110 bg-tn-bg-card")
                                  (when (some? (:archivedAt node)) " opacity-60"))
                   :on-click #(rf/dispatch [::events/select-shared-value (:id node)])}
             [:div.flex.items-center.gap-2
              [bp/icon {:icon "variable" :size 14 :class (when-not selected? "opacity-50")}]
              [:span {:class (str (when selected? "font-semibold")
                                  (when (some? (:archivedAt node)) " line-through"))}
               (:name node)]]
             [bp/button {:icon     "edit"
                         :minimal  true
                         :small    true
                         :class    "opacity-50 hover:opacity-100"
                         :on-click (fn [e]
                                     (.stopPropagation e)
                                     (rf/dispatch [::events/open-shared-value-dialog node]))}]]))
        [load-more/load-more-button
         {:has-next? (:hasNextPage page-info)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-shared-values])}]])]))

;; ---------------------------------------------------------------------------
;; Right panel -- revisions for selected shared value
;; ---------------------------------------------------------------------------

(defn- revisions-main []
  (let [{:keys [selected-id edges revisions revisions-page-info current-only]} @(rf/subscribe [::subs/shared-values-page])
        loading?  @(rf/subscribe [::subs/loading? :revisions])
        rev-edges (:edges revisions)
        rev-pi    revisions-page-info
        sv-name   (some (fn [edge]
                          (when (= (get-in edge [:node :id]) selected-id)
                            (get-in edge [:node :name])))
                        edges)]
    [:div.flex-1.pl-4
     (if-not selected-id
       [states/empty-state {:icon        "variable"
                            :title       "Select a shared value"
                            :description "Choose a shared value from the left to view its revisions."}]
       [:<>
        [:div.flex.items-center.justify-between.mb-4
         [:h3.bp6-heading (or sv-name "Revisions")]
         [:div.flex.items-center.gap-2
          [bp/switch-control {:checked   (boolean current-only)
                              :label     "Current only"
                              :class     "mb-0"
                              :on-change (fn [_] (rf/dispatch [::events/toggle-revisions-current-only]))}]
          [bp/button {:icon "plus" :text "New Revision" :intent "primary" :minimal true
                      :on-click #(rf/dispatch [::events/open-revision-dialog selected-id])}]
          [bp/button {:icon "refresh" :minimal true :loading loading?
                      :on-click #(rf/dispatch [::events/fetch-revisions selected-id])}]
          [bp/button {:icon "cross" :minimal true
                      :on-click #(rf/dispatch [::events/select-shared-value nil])}]]]

        (cond
          (and loading? (empty? rev-edges))
          [states/loading-spinner]

          (empty? rev-edges)
          [:p.text-tn-fg-muted.text-sm "No revisions yet for this shared value."]

          :else
          [:div
           (for [edge rev-edges]
             (let [{:keys [id dimensions value isCurrent createdAt]} (:node edge)]
               ^{:key id}
               [:div {:class (str "mb-2 rounded p-3 transition-all bg-tn-bg-card"
                                  (when isCurrent " ring-1 ring-tn-blue/50"))}
                [:div.flex.items-center.justify-between.mb-1
                 [:div.flex.items-center.gap-2
                  [dimensions-label/dimensions-label dimensions]
                  (when isCurrent
                    [bp/tag {:intent "success" :minimal true} "current"])]
                 [:div.flex.items-center.gap-2
                  [current-status/current-status-controls
                   {:is-current?     isCurrent
                    :on-make-current #(rf/dispatch [::events/set-revision-current id true])
                    :on-deactivate   #(rf/dispatch [::events/set-revision-current id false])}]
                  [:span.text-xs.text-tn-fg-dim createdAt]]]
                [json-block/json-block {:value value :class "text-xs mt-1"}]]))
           [load-more/load-more-button
            {:has-next? (:hasNextPage rev-pi)
             :loading?  loading?
             :on-click  #(rf/dispatch [::events/load-more-revisions])}]])])]))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn shared-values-screen []
  [:div {:class "max-w-4xl mx-auto px-4 py-4"}
   [:div.flex
    [shared-values-sidebar]
    [revisions-main]]
   [shared-value-dialog]
   [revision-dialog]])
