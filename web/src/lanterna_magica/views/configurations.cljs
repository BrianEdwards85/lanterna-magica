(ns lanterna-magica.views.configurations
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.events :as events]
            [lanterna-magica.subs :as subs]
            [lanterna-magica.views.components :as comp]
            [lanterna-magica.components.select :as sel]
            [re-frame.core :as rf]
            [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create Configuration Dialog
;; ---------------------------------------------------------------------------

(defn configuration-dialog []
  (let [{:keys [open? configuration]} @(rf/subscribe [::subs/configuration-dialog])
        saving?      @(rf/subscribe [::subs/loading? :save-configuration])
        error        @(rf/subscribe [::subs/error :save-configuration])
        services     @(rf/subscribe [::subs/services-dropdown-items])
        environments @(rf/subscribe [::subs/environments-dropdown-items])]
    (when open?
      [bp/dialog {:title    "Create Configuration"
                  :icon     "document"
                  :is-open  true
                  :on-close #(rf/dispatch [::events/close-configuration-dialog])
                  :class    "w-full max-w-lg"}
       [bp/dialog-body
        [:div {:class "mb-4 flex items-center gap-3"}
         [:label.bp6-label.shrink-0 {:style {:margin 0 :line-height "30px"}} "Service"]
         [:div.flex-1
          [sel/searchable-select
           {:items            services
            :selected-id      (:serviceId configuration)
            :on-select        #(rf/dispatch [::events/set-configuration-field :serviceId %])
            :on-query-change  [::events/search-services-list]
            :on-clear-search  [::events/clear-services-search-results]
            :icon             "applications"
            :placeholder      "Select service..."}]]]
        [:div {:class "mb-4 flex items-center gap-3"}
         [:label.bp6-label.shrink-0 {:style {:margin 0 :line-height "30px"}} "Environment"]
         [:div.flex-1
          [sel/searchable-select
           {:items            environments
            :selected-id      (:environmentId configuration)
            :on-select        #(rf/dispatch [::events/set-configuration-field :environmentId %])
            :on-query-change  [::events/search-environments-list]
            :on-clear-search  [::events/clear-environments-search-results]
            :icon             "globe-network"
            :placeholder      "Select environment..."}]]]
        [:div.mb-4
         [:label.bp6-label "Configuration Body (JSON)"]
         [comp/local-textarea {:rows        12
                               :value       (or (:body-text configuration) "")
                               :class       "font-mono text-sm"
                               :placeholder "{\n  \"key\": \"value\"\n}"
                               :on-change   #(rf/dispatch [::events/set-configuration-field :body-text %])}]]
        (when error
          [comp/error-banner "Failed to create configuration. Check your JSON."])]
       [bp/dialog-footer
        {:actions
         (r/as-element
          [:<>
           [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-configuration-dialog])}]
           [bp/button {:text "Create" :intent "primary" :icon "tick"
                       :loading saving?
                       :on-click #(rf/dispatch [::events/save-configuration])}]])}]])))

;; ---------------------------------------------------------------------------
;; Configuration Detail Panel
;; ---------------------------------------------------------------------------

(defn config-detail-panel []
  (let [page     @(rf/subscribe [::subs/configurations-page])
        config   (:selected page)
        loading? @(rf/subscribe [::subs/loading? :configuration-detail])]
    (when (:selected-id page)
      [:div {:class "mt-4 p-4 rounded bg-tn-bg-dark border border-tn-border"}
       [:div.flex.items-center.justify-between.mb-3
        [:h4.bp6-heading.m-0 "Configuration Detail"]
        [bp/button {:icon "cross" :minimal true
                    :on-click #(rf/dispatch [::events/select-configuration nil])}]]
       (cond
         loading?
         [comp/loading-spinner]

         (nil? config)
         [:p.text-tn-fg-muted "Configuration not found."]

         :else
         [:div
          [:div.flex.items-center.gap-2.mb-3
           [bp/tag {:minimal true} (str (get-in config [:service :name])
                                        " / "
                                        (get-in config [:environment :name]))]
           (when (:isCurrent config)
             [bp/tag {:intent "success" :minimal true} "current"])
           [:span.text-xs.text-tn-fg-dim (:createdAt config)]]

          [:h5.bp6-heading.mb-2 "Body"]
          [:pre.json-display
           (.stringify js/JSON (clj->js (:body config)) nil 2)]

          (when (seq (:substitutions config))
            [:div.mt-4
             [:h5.bp6-heading.mb-2 "Substitutions"]
             (for [sub (:substitutions config)]
               ^{:key (:id sub)}
               [:div {:class "flex items-center gap-2 mb-1 p-2 rounded bg-tn-bg-card"}
                [bp/icon {:icon "arrow-right" :size 12 :class "text-tn-fg-dim"}]
                [:code.text-sm.text-tn-cyan (:jsonpath sub)]
                [:span.text-tn-fg-dim "\u2192"]
                [bp/tag {:minimal true :intent "primary"}
                 (get-in sub [:sharedValue :name])]])])])])))

;; ---------------------------------------------------------------------------
;; Filter Bar
;; ---------------------------------------------------------------------------

(defn filter-bar []
  (let [services     @(rf/subscribe [::subs/services-dropdown-items])
        environments @(rf/subscribe [::subs/environments-dropdown-items])
        page         @(rf/subscribe [::subs/configurations-page])]
    [:div {:class "flex items-center gap-3 mb-4"}
     [:div.flex-1
      [sel/searchable-select
       {:items            services
        :selected-id      (:filter-service-id page)
        :on-select        #(rf/dispatch [::events/set-config-filter-service %])
        :on-query-change  [::events/search-services-list]
        :on-clear-search  [::events/clear-services-search-results]
        :icon             "applications"
        :placeholder      "All services"}]]
     [:div.flex-1
      [sel/searchable-select
       {:items            environments
        :selected-id      (:filter-environment-id page)
        :on-select        #(rf/dispatch [::events/set-config-filter-environment %])
        :on-query-change  [::events/search-environments-list]
        :on-clear-search  [::events/clear-environments-search-results]
        :icon             "globe-network"
        :placeholder      "All environments"}]]]))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn configurations-screen []
  (let [initial-load (r/atom true)]
    (when @initial-load
      (rf/dispatch [::events/fetch-configurations])
      (reset! initial-load false))
    (fn []
      (let [{:keys [edges page-info selected-id]} @(rf/subscribe [::subs/configurations-page])
            loading?   @(rf/subscribe [::subs/loading? :configurations])
            page-error @(rf/subscribe [::subs/error :configurations])]
        [:div {:class "max-w-2xl mx-auto px-4 py-4"}
         (when page-error
           [comp/error-banner "Failed to load configurations."])

         [comp/page-header {:title      "Configurations"
                            :loading?   loading?
                            :on-refresh #(rf/dispatch [::events/fetch-configurations])
                            :on-create  #(rf/dispatch [::events/open-configuration-dialog])}]

         [filter-bar]

         (cond
           (and loading? (empty? edges))
           [comp/loading-spinner]

           (empty? edges)
           [comp/empty-state {:icon        "document"
                              :title       "No configurations found"
                              :description "Create a configuration or adjust filters."}]

           :else
           [:div
            (for [edge edges]
              (let [node (:node edge)]
                ^{:key (:id node)}
                [:div {:class (str "mb-2 rounded p-3 cursor-pointer transition-all "
                                   "bg-tn-bg-card hover:brightness-110"
                                   (when (= (:id node) selected-id) " ring-1 ring-tn-blue/50"))
                       :on-click #(rf/dispatch [::events/select-configuration (:id node)])}
                 [:div.flex.items-center.justify-between
                  [:div.flex.items-center.gap-2
                   [:span.font-semibold
                    (str (get-in node [:service :name]) " / " (get-in node [:environment :name]))]
                   (when (:isCurrent node)
                     [bp/tag {:intent "success" :minimal true} "current"])]
                  [:span.text-xs.text-tn-fg-dim (:createdAt node)]]]))
            [comp/load-more-button
             {:has-next? (:hasNextPage page-info)
              :loading?  loading?
              :on-click  #(rf/dispatch [::events/load-more-configurations])}]])

         (when selected-id
           [config-detail-panel])

         [configuration-dialog]]))))
