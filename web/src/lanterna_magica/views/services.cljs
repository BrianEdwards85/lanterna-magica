(ns lanterna-magica.views.services
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.events :as events]
            [lanterna-magica.subs :as subs]
            [lanterna-magica.views.components :as comp]
            [re-frame.core :as rf]
            [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create / Edit Dialog
;; ---------------------------------------------------------------------------

(defn service-dialog []
  (let [{:keys [open? editing service]} @(rf/subscribe [::subs/service-dialog])
        saving?    @(rf/subscribe [::subs/loading? :save-service])
        archiving? @(rf/subscribe [::subs/loading? :archive-service])
        save-error @(rf/subscribe [::subs/error :save-service])]
    (when open?
      (let [archived? (some? (:archivedAt service))]
        [bp/dialog {:title    (if editing "Edit Service" "Create Service")
                    :icon     "applications"
                    :is-open  true
                    :on-close #(rf/dispatch [::events/close-service-dialog])
                    :class    "w-full max-w-md"}
         [bp/dialog-body
          (when (and editing archived?)
            [:div {:class "mb-4 p-3 rounded bg-tn-orange/10 text-tn-orange text-sm flex items-center gap-2"}
             [bp/icon {:icon "warning-sign" :size 14}]
             "This service is archived."])

          [:div.mb-4
           [:label.bp6-label "Name"]
           [bp/input-group {:value       (or (:name service) "")
                            :placeholder "my-service"
                            :disabled    (and editing archived?)
                            :on-change   #(rf/dispatch [::events/set-service-field
                                                        :name (.. % -target -value)])}]]
          [:div.mb-4
           [:label.bp6-label "Description " [:span.text-tn-fg-dim "(optional)"]]
           [bp/input-group {:value       (or (:description service) "")
                            :placeholder "What this service does..."
                            :disabled    (and editing archived?)
                            :on-change   #(rf/dispatch [::events/set-service-field
                                                        :description (.. % -target -value)])}]]

          (when save-error
            [comp/error-banner "Failed to save service."])

          (when editing
            [:div {:class "mt-6 pt-4 border-t border-tn-border"}
             (if archived?
               [bp/button {:icon "undo" :text "Unarchive" :intent "success" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/unarchive-service (:id service)])}]
               [bp/button {:icon "trash" :text "Archive" :intent "danger" :minimal true
                           :loading archiving?
                           :on-click #(rf/dispatch [::events/archive-service (:id service)])}])])]

         [bp/dialog-footer
          {:actions
           (r/as-element
            [:<>
             [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-service-dialog])}]
             (when-not archived?
               [bp/button {:text "Save" :intent "primary" :icon "tick"
                           :loading saving?
                           :on-click #(rf/dispatch [::events/save-service])}])])}]]))))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn services-screen []
  (let [initial-load (r/atom true)]
    (when @initial-load
      (rf/dispatch [::events/fetch-services])
      (reset! initial-load false))
    (fn []
      (let [{:keys [search show-archived edges page-info]} @(rf/subscribe [::subs/services-page])
            loading?   @(rf/subscribe [::subs/loading? :services])
            page-error @(rf/subscribe [::subs/error :services])]
        [:div {:class "max-w-2xl mx-auto px-4 py-4"}
         (when page-error
           [comp/error-banner "Failed to load services."])

         [comp/page-header {:title      "Services"
                            :loading?   loading?
                            :on-refresh #(rf/dispatch [::events/fetch-services])
                            :on-create  #(rf/dispatch [::events/open-service-dialog nil])}]

         [comp/search-bar {:search              search
                           :on-search-change    #(rf/dispatch [::events/set-services-search %])
                           :show-archived       show-archived
                           :on-toggle-archived  #(rf/dispatch [::events/toggle-services-archived])
                           :placeholder         "Search services..."}]

         (cond
           (and loading? (empty? edges))
           [comp/loading-spinner]

           (empty? edges)
           [comp/empty-state {:icon        "applications"
                              :title       "No services found"
                              :description (if (seq search)
                                             "Try a different search term."
                                             "Create your first service to get started.")}]

           :else
           [:div
            (for [edge edges]
              ^{:key (get-in edge [:node :id])}
              [comp/entity-card
               {:name        (get-in edge [:node :name])
                :description (get-in edge [:node :description])
                :archived?   (some? (get-in edge [:node :archivedAt]))
                :on-click    #(rf/dispatch [::events/open-service-dialog (:node edge)])}])
            [comp/load-more-button
             {:has-next? (:hasNextPage page-info)
              :loading?  loading?
              :on-click  #(rf/dispatch [::events/load-more-services])}]])

         [service-dialog]]))))
