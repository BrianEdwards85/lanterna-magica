(ns lanterna-magica.views.configurations
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.components.current-status :as current-status]
   [lanterna-magica.components.dimension-picker :as dim-picker]
   [lanterna-magica.components.dimensions-label :as dimensions-label]
   [lanterna-magica.components.error-banner :as error-banner]
   [lanterna-magica.components.inputs :as inputs]
   [lanterna-magica.components.json-block :as json-block]
   [lanterna-magica.components.load-more :as load-more]
   [lanterna-magica.components.select :as sel]
   [lanterna-magica.components.states :as states]
   [lanterna-magica.events :as events]
   [lanterna-magica.subs :as subs]
   [re-frame.core :as rf]
   [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create Configuration Dialog
;; ---------------------------------------------------------------------------

(defn configuration-dialog []
  (let [{:keys [open? configuration]} @(rf/subscribe [::subs/configuration-dialog])
        saving?      @(rf/subscribe [::subs/loading? :save-configuration])
        error        @(rf/subscribe [::subs/error :save-configuration])]
    (when open?
      [bp/dialog {:title    "Create Configuration"
                  :icon     "document"
                  :is-open  true
                  :on-close #(rf/dispatch [::events/close-configuration-dialog])
                  :class    "w-full max-w-lg"}
       [bp/dialog-body
        [dim-picker/dimension-picker
         {:selected-ids (:dimensionIds configuration)
          :on-toggle    #(rf/dispatch [::events/toggle-configuration-dimension %])
          :on-clear     #(rf/dispatch [::events/toggle-configuration-dimension %])}]
        [:div.mb-4
         [:label.bp6-label "Configuration Body (JSON)"]
         [inputs/local-textarea {:rows        12
                                 :value       (or (:body-text configuration) "")
                                 :class       "font-mono text-sm"
                                 :placeholder "{\n  \"key\": \"value\"\n}"
                                 :on-change   #(rf/dispatch [::events/set-configuration-field :body-text %])}]]
        (when error
          [error-banner/error-banner "Failed to create configuration." error])]
       [bp/dialog-footer
        {:actions
         (r/as-element
           [:<>
            [bp/button {:text "Cancel" :on-click #(rf/dispatch [::events/close-configuration-dialog])}]
            [bp/button {:text "Create" :intent "primary" :icon "tick"
                        :loading  saving?
                        :on-click #(rf/dispatch [::events/save-configuration])}]])}]])))

;; ---------------------------------------------------------------------------
;; Left sidebar — filter bar + config list
;; ---------------------------------------------------------------------------

(defn- config-sidebar []
  (let [{:keys [edges page-info selected-id filter-dimension-ids current-only]} @(rf/subscribe [::subs/configurations-page])
        dim-types  @(rf/subscribe [::subs/dimension-types])
        loading?   @(rf/subscribe [::subs/loading? :configurations])
        page-error @(rf/subscribe [::subs/error :configurations])]
    [:div {:class "w-72 shrink-0 border-r border-tn-border pr-3"}
     [:div.flex.items-center.justify-between.mb-3
      [:span.font-semibold.text-sm.text-tn-fg-muted "Configurations"]
      [:div.flex.items-center.gap-1
       [bp/button {:icon     "refresh"
                   :minimal  true
                   :small    true
                   :loading  loading?
                   :on-click #(rf/dispatch [::events/fetch-configurations])}]]]

     ;; Filter dropdowns
     [:div.mb-2
      (for [dt dim-types]
        (let [type-id (:id dt)
              items   @(rf/subscribe [::subs/dimensions-dropdown-items type-id])
              sel-id  (some (set (or filter-dimension-ids [])) (map :id items))]
          ^{:key type-id}
          [:div.mb-2
           [sel/searchable-select
            {:items            items
             :selected-id      sel-id
             :on-select        #(rf/dispatch [::events/set-config-filter-dimension %])
             :on-clear         (when sel-id
                                 #(rf/dispatch [::events/set-config-filter-dimension sel-id]))
             :on-query-change  [::events/search-dimensions-list type-id]
             :on-clear-search  [::events/clear-dimensions-search-results type-id]
             :icon             "tag"
             :placeholder      (str "All " (:name dt) "s")}]]))]

     ;; Current-only toggle + clear filters
     [:div.flex.items-center.justify-between.mb-3
      [bp/switch-control {:checked   (boolean current-only)
                          :label     "Current only"
                          :class     "mb-0"
                          :on-change (fn [_] (rf/dispatch [::events/toggle-configurations-current-only]))}]
      (when (seq filter-dimension-ids)
        [bp/button {:icon "cross" :text "Clear" :minimal true :small true
                    :on-click #(rf/dispatch [::events/clear-config-filters])}])]

     (when page-error
       [error-banner/error-banner "Failed to load configurations." page-error])

     ;; Config list
     (cond
       (and loading? (empty? edges))
       [states/loading-spinner]

       (empty? edges)
       [:div.text-sm.text-tn-fg-dim.p-2
        (if (seq filter-dimension-ids)
          "No results."
          "No configurations yet.")]

       :else
       [:div {:class "flex flex-col gap-1"}
        (for [edge edges]
          (let [node (:node edge)
                selected? (= (:id node) selected-id)]
            ^{:key (:id node)}
            [:div {:class    (str "px-3 py-2 rounded cursor-pointer transition-all "
                                  (if selected?
                                    "bg-tn-selection ring-1 ring-tn-blue/50"
                                    "hover:brightness-110 bg-tn-bg-card"))
                   :on-click #(rf/dispatch [::events/select-configuration (:id node)])}
             [:div.flex.items-center.gap-2.flex-wrap
              [dimensions-label/dimensions-label (:dimensions node)]
              (when (:isCurrent node)
                [bp/tag {:intent "success" :minimal true} "current"])]
             [:span.text-xs.text-tn-fg-dim (:createdAt node)]]))
        [load-more/load-more-button
         {:has-next? (:hasNextPage page-info)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-configurations])}]])]))

;; ---------------------------------------------------------------------------
;; Right panel — configuration detail
;; ---------------------------------------------------------------------------

(defn- config-main []
  (let [{:keys [selected-id selected]} @(rf/subscribe [::subs/configurations-page])
        loading? @(rf/subscribe [::subs/loading? :configuration-detail])]
    [:div.flex-1.pl-4
     (if-not selected-id
       [states/empty-state {:icon        "document"
                            :title       "Select a configuration"
                            :description "Choose a configuration from the left to view its details."}]
       [:<>
        [:div.flex.items-center.justify-between.mb-4
         [:h3.bp6-heading "Configuration Detail"]
         [:div.flex.items-center.gap-2
          [bp/button {:icon "plus" :text "Create" :intent "primary" :minimal true
                      :on-click #(rf/dispatch [::events/open-configuration-dialog])}]
          [bp/button {:icon "cross" :minimal true
                      :on-click #(rf/dispatch [::events/select-configuration nil])}]]]

        (cond
          loading?
          [states/loading-spinner]

          (nil? selected)
          [:p.text-tn-fg-muted "Configuration not found."]

          :else
          [:div
           [:div.flex.items-center.justify-between.mb-3
            [:div.flex.items-center.gap-2
             [dimensions-label/dimensions-label (:dimensions selected)]
             (when (:isCurrent selected)
               [bp/tag {:intent "success" :minimal true} "current"])
             [:span.text-xs.text-tn-fg-dim (:createdAt selected)]]
            [current-status/current-status-controls
             {:is-current?     (:isCurrent selected)
              :on-make-current #(rf/dispatch [::events/set-configuration-current (:id selected) true])
              :on-deactivate   #(rf/dispatch [::events/set-configuration-current (:id selected) false])}]]

           [:h5.bp6-heading.mb-2 "Body"]
           [json-block/json-block {:value (:body selected)}]

           (when (seq (:substitutions selected))
             [:div.mt-4
              [:h5.bp6-heading.mb-2 "Substitutions"]
              (for [sub (:substitutions selected)]
                ^{:key (:id sub)}
                [:div {:class "flex items-center gap-2 mb-1 p-2 rounded bg-tn-bg-card"}
                 [bp/icon {:icon "arrow-right" :size 12 :class "text-tn-fg-dim"}]
                 [:code.text-sm.text-tn-cyan (:jsonpath sub)]
                 [:span.text-tn-fg-dim "\u2192"]
                 [bp/tag {:minimal true :intent "primary"}
                  (get-in sub [:sharedValue :name])]])])])])]))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn configurations-screen []
  [:div {:class "max-w-4xl mx-auto px-4 py-4"}
   [:div.flex
    [config-sidebar]
    [config-main]]
   [configuration-dialog]])
