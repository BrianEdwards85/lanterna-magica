(ns lanterna-magica.views.dimension-types
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.events :as events]
            [lanterna-magica.subs :as subs]
            [lanterna-magica.views.components :as comp]
            [re-frame.core :as rf]
            [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create Dimension Type Dialog
;; ---------------------------------------------------------------------------

(defn dimension-type-dialog []
  (let [{:keys [open? dimension-type]} @(rf/subscribe [::subs/dimension-type-dialog])
        saving?    @(rf/subscribe [::subs/loading? :save-dimension-type])
        archiving? @(rf/subscribe [::subs/loading? :archive-dimension-type])
        save-error @(rf/subscribe [::subs/error :save-dimension-type])]
    (when open?
      [bp/dialog {:title    "Create Dimension Type"
                  :icon     "layers"
                  :is-open  true
                  :on-close #(rf/dispatch [::events/close-dimension-type-dialog])
                  :class    "w-full max-w-md"}
       [bp/dialog-body
        [:div.mb-4
         [:label.bp6-label "Name"]
         [comp/local-input {:value       (or (:name dimension-type) "")
                            :placeholder "e.g. region"
                            :on-change   #(rf/dispatch [::events/set-dimension-type-field :name %])}]]
        [:div.mb-4
         [:label.bp6-label "Priority"]
         [comp/local-input {:value       (str (or (:priority dimension-type) 0))
                            :placeholder "0"
                            :on-change   #(rf/dispatch [::events/set-dimension-type-field :priority (js/parseInt % 10)])}]]
        (when save-error
          [comp/error-banner "Failed to create dimension type."])]
       [bp/dialog-footer
        {:actions
         (r/as-element
          [:<>
           [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-dimension-type-dialog])}]
           [bp/button {:text "Create" :intent "primary" :icon "tick"
                       :loading saving?
                       :on-click #(rf/dispatch [::events/save-dimension-type])}]])}]])))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn dimension-types-screen []
  (let [dim-types      @(rf/subscribe [::subs/dimension-types])
        show-archived  @(rf/subscribe [::subs/show-archived-types])
        loading?       @(rf/subscribe [::subs/loading? :dimension-types])
        archiving?     @(rf/subscribe [::subs/loading? :archive-dimension-type])
        page-error     @(rf/subscribe [::subs/error :dimension-types])]
    [:div {:class "max-w-2xl mx-auto px-4 py-4"}
     (when page-error
       [comp/error-banner "Failed to load dimension types."])

     [comp/page-header {:title      "Dimension Types"
                        :loading?   loading?
                        :on-refresh #(rf/dispatch [::events/fetch-dimension-types])
                        :on-create  #(rf/dispatch [::events/open-dimension-type-dialog])}]

     [:div {:class "flex items-center gap-3 mb-4"}
      [comp/archive-toggle {:checked   show-archived
                            :on-change #(rf/dispatch [::events/toggle-dimension-types-archived])}]]

     (cond
       (and loading? (empty? dim-types))
       [comp/loading-spinner]

       (empty? dim-types)
       [comp/empty-state {:icon        "layers"
                          :title       "No dimension types found"
                          :description "Create your first dimension type to get started."}]

       :else
       [:div
        (for [dt dim-types]
          (let [archived? (some? (:archivedAt dt))]
            ^{:key (:id dt)}
            [:div {:class (str "mb-2 rounded p-3 bg-tn-bg-card"
                               (when archived? " opacity-60"))}
             [:div.flex.items-center.justify-between
              [:div.flex.items-center.gap-2
               [:span {:class (str "font-semibold" (when archived? " line-through"))}
                (:name dt)]
               [bp/tag {:minimal true} (str "priority: " (:priority dt))]
               (when archived?
                 [bp/tag {:minimal true :class "ml-2"} "archived"])]
              [:div.flex.items-center.gap-1
               (if archived?
                 [bp/button {:icon "undo" :minimal true :small true :intent "success"
                             :loading archiving?
                             :on-click #(rf/dispatch [::events/unarchive-dimension-type (:id dt)])}]
                 [bp/button {:icon "trash" :minimal true :small true :intent "danger"
                             :loading archiving?
                             :on-click #(rf/dispatch [::events/archive-dimension-type (:id dt)])}])]]]))])

     [dimension-type-dialog]]))
