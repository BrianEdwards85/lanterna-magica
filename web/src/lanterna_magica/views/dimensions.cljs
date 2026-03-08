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
            [comp/error-banner "Failed to save dimension." save-error])

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
;; Create Dimension Type Dialog
;; ---------------------------------------------------------------------------

(defn- dimension-type-dialog []
  (let [{:keys [open? editing dimension-type]} @(rf/subscribe [::subs/dimension-type-dialog])
        saving?    @(rf/subscribe [::subs/loading? :save-dimension-type])
        archiving? @(rf/subscribe [::subs/loading? :archive-dimension-type])
        save-error @(rf/subscribe [::subs/error :save-dimension-type])]
    (when open?
      (let [archived? (some? (:archivedAt dimension-type))]
        [bp/dialog {:title    (if editing "Edit Dimension Type" "Create Dimension Type")
                    :icon     "layers"
                    :is-open  true
                    :on-close #(rf/dispatch [::events/close-dimension-type-dialog])
                    :class    "w-full max-w-md"}
         [bp/dialog-body
          (when (and editing archived?)
            [:div {:class "mb-4 p-3 rounded bg-tn-orange/10 text-tn-orange text-sm flex items-center gap-2"}
             [bp/icon {:icon "warning-sign" :size 14}]
             "This dimension type is archived."])
          [:div.mb-4
           [:label.bp6-label "Name"]
           [comp/local-input {:value       (or (:name dimension-type) "")
                              :placeholder "e.g. region"
                              :disabled    (and editing archived?)
                              :on-change   #(rf/dispatch [::events/set-dimension-type-field :name %])}]]
          (when save-error
            [comp/error-banner (str "Failed to " (if editing "update" "create") " dimension type.") save-error])
          (when editing
            [:div {:class "mt-6 pt-4 border-t border-tn-border"}
             (if archived?
               [bp/button {:icon "undo" :text "Unarchive" :intent "success" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/unarchive-dimension-type (:id dimension-type)])}]
               [bp/button {:icon "trash" :text "Archive" :intent "danger" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/archive-dimension-type (:id dimension-type)])}])])]
         [bp/dialog-footer
          {:actions
           (r/as-element
            [:<>
             [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-dimension-type-dialog])}]
             (when-not archived?
               [bp/button {:text "Save" :intent "primary" :icon "tick"
                           :loading saving?
                           :on-click #(rf/dispatch [::events/save-dimension-type])}])])}]]))))

;; ---------------------------------------------------------------------------
;; Left sidebar — dimension type list
;; ---------------------------------------------------------------------------

(defn- type-list-item [dt selected? first? last?]
  [:div {:class    (str "px-3 py-2 rounded cursor-pointer transition-all flex items-center justify-between "
                        (if selected?
                          "bg-tn-selection ring-1 ring-tn-blue/50"
                          "hover:brightness-110 bg-tn-bg-card")
                        (when (some? (:archivedAt dt)) " opacity-60"))
         :on-click #(rf/dispatch [::events/select-dimension-type (:id dt)])}
   [:div.flex.items-center.gap-2
    [bp/icon {:icon "layers" :size 14 :class (when-not selected? "opacity-50")}]
    [:span {:class (str (when selected? "font-semibold")
                        (when (some? (:archivedAt dt)) " line-through"))} (:name dt)]]
   [:div.flex.items-center.gap-0
    [bp/button {:icon     "chevron-up"
                :minimal  true
                :small    true
                :disabled first?
                :class    "opacity-50 hover:opacity-100"
                :on-click (fn [e]
                            (.stopPropagation e)
                            (rf/dispatch [::events/move-dimension-type (:id dt) :up]))}]
    [bp/button {:icon     "chevron-down"
                :minimal  true
                :small    true
                :disabled last?
                :class    "opacity-50 hover:opacity-100"
                :on-click (fn [e]
                            (.stopPropagation e)
                            (rf/dispatch [::events/move-dimension-type (:id dt) :down]))}]
    [bp/button {:icon     "edit"
                :minimal  true
                :small    true
                :class    "opacity-50 hover:opacity-100"
                :on-click (fn [e]
                            (.stopPropagation e)
                            (rf/dispatch [::events/open-dimension-type-dialog dt]))}]]])

(defn- type-sidebar []
  (let [dim-types      @(rf/subscribe [::subs/dimension-types])
        show-archived  @(rf/subscribe [::subs/show-archived-types])
        selected       @(rf/subscribe [::subs/selected-dimension-type-id])
        loading?       @(rf/subscribe [::subs/loading? :dimension-types])]
    [:div {:class "w-56 shrink-0 border-r border-tn-border pr-3"}
     [:div.flex.items-center.justify-between.mb-3
      [:span.font-semibold.text-sm.text-tn-fg-muted "Dimension Types"]
      [:div.flex.items-center.gap-1
       [bp/button {:icon     "plus"
                   :minimal  true
                   :small    true
                   :on-click #(rf/dispatch [::events/open-dimension-type-dialog])}]
       [bp/button {:icon     "refresh"
                   :minimal  true
                   :small    true
                   :loading  loading?
                   :on-click #(rf/dispatch [::events/fetch-dimension-types])}]]]
     [:div.mb-3
      [comp/archive-toggle {:checked   show-archived
                            :on-change #(rf/dispatch [::events/toggle-dimension-types-archived])}]]
     (cond
       (and loading? (empty? dim-types))
       [comp/loading-spinner]

       (empty? dim-types)
       [:div.text-sm.text-tn-fg-dim.p-2 "No dimension types yet."]

       :else
       (let [last-idx (dec (count dim-types))]
         [:div {:class "flex flex-col gap-1"}
          (for [[idx dt] (map-indexed vector dim-types)]
            ^{:key (:id dt)}
            [type-list-item dt (= (:id dt) selected) (zero? idx) (= idx last-idx)])]))]))

;; ---------------------------------------------------------------------------
;; Right panel — dimensions for selected type
;; ---------------------------------------------------------------------------

(defn- dimensions-main []
  (let [selected-id @(rf/subscribe [::subs/selected-dimension-type-id])
        dim-types   @(rf/subscribe [::subs/dimension-types])
        sel-type    (some #(when (= (:id %) selected-id) %) dim-types)]
    (if-not sel-type
      [comp/empty-state {:icon        "tag"
                         :title       "Select a dimension type"
                         :description "Choose a dimension type from the left to view its dimensions."}]
      (let [type-id    (:id sel-type)
            type-name  (:name sel-type)
            page       @(rf/subscribe [::subs/dimensions-page type-id])
            {:keys [search show-archived edges page-info]} page
            loading?   @(rf/subscribe [::subs/loading? :dimensions])
            page-error @(rf/subscribe [::subs/error :dimensions])]
        [:div.flex-1.pl-4
         (when page-error
           [comp/error-banner (str "Failed to load " type-name " dimensions.") page-error])

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
              :on-click  #(rf/dispatch [::events/load-more-dimensions type-id])}]])]))))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn dimensions-screen []
  [:div {:class "max-w-4xl mx-auto px-4 py-4"}
   [:div.flex
    [type-sidebar]
    [dimensions-main]]
   [dimension-dialog]
   [dimension-type-dialog]])
