(ns lanterna-magica.views.dimensions
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.events :as events]
            [lanterna-magica.subs :as subs]
            [lanterna-magica.views.components :as comp]
            [re-frame.core :as rf]
            [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create / Edit Dimension Dialog
;; ---------------------------------------------------------------------------

(defn dimension-dialog []
  (let [{:keys [open? editing dimension type-id]} @(rf/subscribe [::subs/dimension-dialog])
        saving?    @(rf/subscribe [::subs/loading? :save-dimension])
        archiving? @(rf/subscribe [::subs/loading? :archive-dimension])
        save-error @(rf/subscribe [::subs/error :save-dimension])]
    (when open?
      (let [archived? (some? (:archivedAt dimension))]
        [bp/dialog {:title    (if editing "Edit Dimension" "Create Dimension")
                    :icon     "tag"
                    :is-open  true
                    :on-close #(rf/dispatch [::events/close-dimension-dialog])
                    :class    "w-full max-w-md"}
         [bp/dialog-body
          (when (and editing archived?)
            [:div {:class "mb-4 p-3 rounded bg-tn-orange/10 text-tn-orange text-sm flex items-center gap-2"}
             [bp/icon {:icon "warning-sign" :size 14}]
             "This dimension is archived."])

          [:div.mb-4
           [:label.bp6-label "Name"]
           [comp/local-input {:value       (or (:name dimension) "")
                              :placeholder "e.g. production"
                              :disabled    (and editing archived?)
                              :on-change   #(rf/dispatch [::events/set-dimension-field :name %])}]]
          [:div.mb-4
           [:label.bp6-label "Description " [:span.text-tn-fg-dim "(optional)"]]
           [comp/local-input {:value       (or (:description dimension) "")
                              :placeholder "What this dimension represents..."
                              :disabled    (and editing archived?)
                              :on-change   #(rf/dispatch [::events/set-dimension-field :description %])}]]

          (when save-error
            [comp/error-banner "Failed to save dimension."])

          (when editing
            [:div {:class "mt-6 pt-4 border-t border-tn-border"}
             (if archived?
               [bp/button {:icon "undo" :text "Unarchive" :intent "success" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/unarchive-dimension type-id (:id dimension)])}]
               [bp/button {:icon "trash" :text "Archive" :intent "danger" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/archive-dimension type-id (:id dimension)])}])])]

         [bp/dialog-footer
          {:actions
           (r/as-element
            [:<>
             [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-dimension-dialog])}]
             (when-not archived?
               [bp/button {:text "Save" :intent "primary" :icon "tick"
                           :loading saving?
                           :on-click #(rf/dispatch [::events/save-dimension])}])])}]]))))

;; ---------------------------------------------------------------------------
;; Dimensions list for a single type
;; ---------------------------------------------------------------------------

(defn dimensions-panel [type-id type-name]
  (let [page       @(rf/subscribe [::subs/dimensions-page type-id])
        {:keys [search show-archived edges page-info]} page
        loading?   @(rf/subscribe [::subs/loading? :dimensions])
        page-error @(rf/subscribe [::subs/error :dimensions])]
    [:div {:class "mt-4"}
     (when page-error
       [comp/error-banner (str "Failed to load " type-name " dimensions.")])

     [comp/page-header {:title      type-name
                        :loading?   loading?
                        :on-refresh #(rf/dispatch [::events/fetch-dimensions type-id])
                        :on-create  #(rf/dispatch [::events/open-dimension-dialog type-id nil])}]

     [comp/search-bar {:search              (or search "")
                       :on-search-change    #(rf/dispatch [::events/set-dimensions-search type-id %])
                       :show-archived       show-archived
                       :on-toggle-archived  #(rf/dispatch [::events/toggle-dimensions-archived type-id])
                       :placeholder         (str "Search " type-name "...")}]

     (cond
       (and loading? (empty? edges))
       [comp/loading-spinner]

       (empty? edges)
       [comp/empty-state {:icon        "tag"
                          :title       (str "No " type-name " found")
                          :description (if (seq search)
                                         "Try a different search term."
                                         "Create your first dimension to get started.")}]

       :else
       [:div
        (for [edge edges]
          ^{:key (get-in edge [:node :id])}
          [comp/entity-card
           {:name        (get-in edge [:node :name])
            :description (get-in edge [:node :description])
            :archived?   (some? (get-in edge [:node :archivedAt]))
            :on-click    #(rf/dispatch [::events/open-dimension-dialog type-id (:node edge)])}])
        [comp/load-more-button
         {:has-next? (:hasNextPage page-info)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-dimensions type-id])}]])]))

;; ---------------------------------------------------------------------------
;; Screen — shows all dimension types with their dimensions
;; ---------------------------------------------------------------------------

(defn dimensions-screen []
  (let [dim-types @(rf/subscribe [::subs/dimension-types])
        loading?  @(rf/subscribe [::subs/loading? :dimension-types])]
    [:div {:class "max-w-2xl mx-auto px-4 py-4"}
     (cond
       (and loading? (empty? dim-types))
       [comp/loading-spinner]

       (empty? dim-types)
       [comp/empty-state {:icon        "layers"
                          :title       "No dimension types"
                          :description "Create dimension types to organize your dimensions."}]

       :else
       (for [dt dim-types]
         ^{:key (:id dt)}
         [dimensions-panel (:id dt) (:name dt)]))

     [dimension-dialog]]))
