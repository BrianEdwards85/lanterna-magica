(ns lanterna-magica.views.environments
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.events :as events]
            [lanterna-magica.subs :as subs]
            [lanterna-magica.views.components :as comp]
            [re-frame.core :as rf]
            [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create / Edit Dialog
;; ---------------------------------------------------------------------------

(defn environment-dialog []
  (let [{:keys [open? editing environment]} @(rf/subscribe [::subs/environment-dialog])
        saving?    @(rf/subscribe [::subs/loading? :save-environment])
        archiving? @(rf/subscribe [::subs/loading? :archive-environment])
        save-error @(rf/subscribe [::subs/error :save-environment])]
    (when open?
      (let [archived? (some? (:archivedAt environment))]
        [bp/dialog {:title    (if editing "Edit Environment" "Create Environment")
                    :icon     "globe-network"
                    :is-open  true
                    :on-close #(rf/dispatch [::events/close-environment-dialog])
                    :class    "w-full max-w-md"}
         [bp/dialog-body
          (when (and editing archived?)
            [:div {:class "mb-4 p-3 rounded bg-tn-orange/10 text-tn-orange text-sm flex items-center gap-2"}
             [bp/icon {:icon "warning-sign" :size 14}]
             "This environment is archived."])

          [:div.mb-4
           [:label.bp6-label "Name"]
           [comp/local-input {:value       (or (:name environment) "")
                              :placeholder "production"
                              :disabled    (and editing archived?)
                              :on-change   #(rf/dispatch [::events/set-environment-field :name %])}]]
          [:div.mb-4
           [:label.bp6-label "Description " [:span.text-tn-fg-dim "(optional)"]]
           [comp/local-input {:value       (or (:description environment) "")
                              :placeholder "Production environment"
                              :disabled    (and editing archived?)
                              :on-change   #(rf/dispatch [::events/set-environment-field :description %])}]]

          (when save-error
            [comp/error-banner "Failed to save environment."])

          (when editing
            [:div {:class "mt-6 pt-4 border-t border-tn-border"}
             (if archived?
               [bp/button {:icon "undo" :text "Unarchive" :intent "success" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/unarchive-environment (:id environment)])}]
               [bp/button {:icon "trash" :text "Archive" :intent "danger" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/archive-environment (:id environment)])}])])]

         [bp/dialog-footer
          {:actions
           (r/as-element
            [:<>
             [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-environment-dialog])}]
             (when-not archived?
               [bp/button {:text "Save" :intent "primary" :icon "tick"
                           :loading saving?
                           :on-click #(rf/dispatch [::events/save-environment])}])])}]]))))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn environments-screen []
  (let [{:keys [search show-archived edges page-info]} @(rf/subscribe [::subs/environments-page])
        loading?   @(rf/subscribe [::subs/loading? :environments])
        page-error @(rf/subscribe [::subs/error :environments])]
    [:div {:class "max-w-2xl mx-auto px-4 py-4"}
     (when page-error
       [comp/error-banner "Failed to load environments."])

     [comp/page-header {:title      "Environments"
                        :loading?   loading?
                        :on-refresh #(rf/dispatch [::events/fetch-environments])
                        :on-create  #(rf/dispatch [::events/open-environment-dialog nil])}]

     [comp/search-bar {:search              search
                       :on-search-change    #(rf/dispatch [::events/set-environments-search %])
                       :show-archived       show-archived
                       :on-toggle-archived  #(rf/dispatch [::events/toggle-environments-archived])
                       :placeholder         "Search environments..."}]

     (cond
       (and loading? (empty? edges))
       [comp/loading-spinner]

       (empty? edges)
       [comp/empty-state {:icon        "globe-network"
                          :title       "No environments found"
                          :description (if (seq search)
                                         "Try a different search term."
                                         "Create your first environment to get started.")}]

       :else
       [:div
        (for [edge edges]
          ^{:key (get-in edge [:node :id])}
          [comp/entity-card
           {:name        (get-in edge [:node :name])
            :description (get-in edge [:node :description])
            :archived?   (some? (get-in edge [:node :archivedAt]))
            :on-click    #(rf/dispatch [::events/open-environment-dialog (:node edge)])}])
        [comp/load-more-button
         {:has-next? (:hasNextPage page-info)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-environments])}]])

     [environment-dialog]]))
