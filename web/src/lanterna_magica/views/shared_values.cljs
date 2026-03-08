(ns lanterna-magica.views.shared-values
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.components.dimension-picker :as dim-picker]
            [lanterna-magica.events :as events]
            [lanterna-magica.subs :as subs]
            [lanterna-magica.views.components :as comp]
            [re-frame.core :as rf]
            [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Helpers
;; ---------------------------------------------------------------------------

(defn- dimensions-label [dimensions]
  [:div.flex.items-center.gap-1.flex-wrap
   (for [dim dimensions]
     ^{:key (:id dim)}
     [bp/tag {:minimal true}
      (str (get-in dim [:type :name]) ": " (:name dim))])])

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
            [:div {:class "mb-4 p-3 rounded bg-tn-orange/10 text-tn-orange text-sm flex items-center gap-2"}
             [bp/icon {:icon "warning-sign" :size 14}]
             "This shared value is archived."])
          [:div.mb-4
           [:label.bp6-label "Name"]
           [comp/local-input {:value       (or (:name shared-value) "")
                              :placeholder "DATABASE_URL"
                              :disabled    (and editing archived?)
                              :on-change   #(rf/dispatch [::events/set-shared-value-field :name %])}]]
          (when error
            [comp/error-banner "Failed to save shared value." error])
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
         [comp/local-textarea {:rows        6
                               :value       (or (:value-text revision) "")
                               :placeholder "{\"key\": \"value\"}"
                               :class       "font-mono text-sm"
                               :on-change   #(rf/dispatch [::events/set-revision-field :value-text %])}]]
        (when error
          [comp/error-banner "Failed to create revision." error])]
       [bp/dialog-footer
        {:actions
         (r/as-element
          [:<>
           [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-revision-dialog])}]
           [bp/button {:text "Create" :intent "primary" :icon "tick"
                       :loading  saving?
                       :on-click #(rf/dispatch [::events/save-revision])}]])}]])))

;; ---------------------------------------------------------------------------
;; Revisions Panel
;; ---------------------------------------------------------------------------

(defn revisions-panel [selected-id]
  (let [page          @(rf/subscribe [::subs/shared-values-page])
        revisions     (get-in page [:revisions :edges])
        rev-pi        (:revisions-page-info page)
        current-only  (:current-only page)
        loading?      @(rf/subscribe [::subs/loading? :revisions])
        sv-name       (some (fn [edge]
                              (when (= (get-in edge [:node :id]) selected-id)
                                (get-in edge [:node :name])))
                            (:edges page))]
    [:div {:class "mt-4 p-4 rounded bg-tn-bg-dark border border-tn-border"}
     [:div.flex.items-center.justify-between.mb-3
      [:h4.bp6-heading.m-0 (str "Revisions" (when sv-name (str " — " sv-name)))]
      [:div.flex.items-center.gap-2
       [bp/switch-control {:checked   (boolean current-only)
                           :label     "Current only"
                           :class     "mb-0"
                           :on-change (fn [_] (rf/dispatch [::events/toggle-revisions-current-only]))}]
       [bp/button {:icon "plus" :text "New Revision" :minimal true :intent "primary"
                   :on-click #(rf/dispatch [::events/open-revision-dialog selected-id])}]
       [bp/button {:icon "cross" :minimal true
                   :on-click #(rf/dispatch [::events/select-shared-value nil])}]]]
     (cond
       (and loading? (empty? revisions))
       [comp/loading-spinner]

       (empty? revisions)
       [:p.text-tn-fg-muted.text-sm "No revisions yet for this shared value."]

       :else
       [:div
        (for [edge revisions]
          (let [{:keys [id dimensions value isCurrent createdAt]} (:node edge)]
            ^{:key id}
            [:div {:class (str "mb-2 rounded p-3 transition-all bg-tn-bg-card"
                               (when isCurrent " ring-1 ring-tn-blue/50"))}
             [:div.flex.items-center.justify-between.mb-1
              [:div.flex.items-center.gap-2
               [dimensions-label dimensions]
               (when isCurrent
                 [bp/tag {:intent "success" :minimal true} "current"])]
              [:div.flex.items-center.gap-2
               (if isCurrent
                 [bp/button {:text "Deactivate" :minimal true :small true
                             :intent "danger"
                             :on-click #(rf/dispatch [::events/set-revision-current id false])}]
                 [bp/button {:text "Make Current" :minimal true :small true
                             :intent "success"
                             :on-click #(rf/dispatch [::events/set-revision-current id true])}])
               [:span.text-xs.text-tn-fg-dim createdAt]]]
             [:pre.json-display.text-xs.mt-1
              (.stringify js/JSON (clj->js value) nil 2)]]))
        [comp/load-more-button
         {:has-next? (:hasNextPage rev-pi)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-revisions])}]])]))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn shared-values-screen []
  (let [{:keys [search show-archived edges page-info selected-id]} @(rf/subscribe [::subs/shared-values-page])
        loading?   @(rf/subscribe [::subs/loading? :shared-values])
        page-error @(rf/subscribe [::subs/error :shared-values])]
    [:div {:class "max-w-2xl mx-auto px-4 py-4"}
     (when page-error
       [comp/error-banner "Failed to load shared values." page-error])

     [comp/page-header {:title      "Shared Values"
                        :loading?   loading?
                        :on-refresh #(rf/dispatch [::events/fetch-shared-values])
                        :on-create  #(rf/dispatch [::events/open-shared-value-dialog])}]

     [comp/search-bar {:search              (or search "")
                       :on-search-change    #(rf/dispatch [::events/set-shared-values-search %])
                       :show-archived       show-archived
                       :on-toggle-archived  #(rf/dispatch [::events/toggle-shared-values-archived])
                       :placeholder         "Search shared values..."}]

     (cond
       (and loading? (empty? edges))
       [comp/loading-spinner]

       (empty? edges)
       [comp/empty-state {:icon        "variable"
                          :title       "No shared values found"
                          :description (if (seq search)
                                         "Try a different search term."
                                         "Create your first shared value to get started.")}]

       :else
       [:div
        (for [edge edges]
          (let [node (:node edge)]
            ^{:key (:id node)}
            [comp/entity-card
             {:name      (:name node)
              :archived? (some? (:archivedAt node))
              :badges    [^{:key "revisions"}
                          [bp/button
                           {:icon "history" :minimal true :small true
                            :title "View revisions"
                            :intent (when (= (:id node) selected-id) "primary")
                            :on-click (fn [e]
                                        (.stopPropagation e)
                                        (rf/dispatch [::events/select-shared-value
                                                      (when-not (= (:id node) selected-id)
                                                        (:id node))]))}]]
              :on-click  #(rf/dispatch [::events/open-shared-value-dialog node])}]))
        [comp/load-more-button
         {:has-next? (:hasNextPage page-info)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-shared-values])}]])

     (when selected-id
       [revisions-panel selected-id])

     [shared-value-dialog]
     [revision-dialog]]))
