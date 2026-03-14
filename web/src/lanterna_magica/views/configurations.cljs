(ns lanterna-magica.views.configurations
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.components.debounce :as deb]
   [lanterna-magica.components.dimension-picker :as dim-picker]
   [lanterna-magica.components.dimensions-label :as dimensions-label]
   [lanterna-magica.components.error-banner :as error-banner]
   [lanterna-magica.components.json-block :as json-block]
   [lanterna-magica.components.load-more :as load-more]
   [lanterna-magica.components.monaco-editor :as monaco]
   [lanterna-magica.components.select :as sel]
   [lanterna-magica.components.states :as states]
   [lanterna-magica.components.timestamp :as timestamp]
   [lanterna-magica.events :as events]
   [lanterna-magica.subs :as subs]
   [re-frame.core :as rf]
   [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create Configuration Dialog — single-step side-by-side layout
;; ---------------------------------------------------------------------------

(defn configuration-dialog []
  ;; NOTE: r/with-let is intentional here. Do NOT convert this to
  ;; (r/create-class ...) inside a defn body. That pattern causes Reagent
  ;; to produce a new React component class on every parent re-render,
  ;; remounting the component and resetting cursor position in the textarea.
  ;; This is the second time this bug has been introduced.
  (r/with-let [debounced-extract (deb/make-debounced-fn
                                   #(rf/dispatch [::events/extract-sentinel-paths]))]
    (let [{:keys [open? configuration]} @(rf/subscribe [::subs/configuration-dialog])
          sentinel-paths    @(rf/subscribe [::subs/config-sentinel-paths])
          substitutions     @(rf/subscribe [::subs/config-substitutions])
          resolved-values   @(rf/subscribe [::subs/config-resolved-values])
          body-valid?       @(rf/subscribe [::subs/config-body-valid?])
          extraction-pending? @(rf/subscribe [::subs/config-extraction-pending?])
          saving?           @(rf/subscribe [::subs/loading? :save-configuration])
          extracting?       @(rf/subscribe [::subs/loading? :extract-sentinel-paths])
          error             @(rf/subscribe [::subs/error :save-configuration])
          {:keys [edges]}   @(rf/subscribe [::subs/shared-values-page])
          sv-items          (mapv :node edges)
          all-mapped?       (every? #(get substitutions %) sentinel-paths)
          save-disabled?    (or extraction-pending?
                                extracting?
                                (false? body-valid?)
                                (not all-mapped?))]
      (when open?
        [bp/dialog {:title    "Create Configuration"
                    :icon     "document"
                    :is-open  true
                    :on-close #(rf/dispatch [::events/close-configuration-dialog])
                    :class    "w-full max-w-3xl"}
         [bp/dialog-body
          [:div.flex.gap-4
           ;; Left column: dimension picker + JSON body editor
           [:div {:style {:flex "0 0 55%"}}
            [dim-picker/dimension-picker
             {:selected-ids (:dimensionIds configuration)
              :on-toggle    #(rf/dispatch [::events/toggle-configuration-dimension %])
              :on-clear     #(rf/dispatch [::events/toggle-configuration-dimension %])}]
            [:div.mb-4
             [:label.bp6-label "Configuration Body (JSON)"]
             [monaco/monaco-editor
              {:value     (or (:body-text configuration) "{}")
               :language  "json"
               :height    "320px"
               :on-change (fn [v]
                            (rf/dispatch [::events/set-configuration-body v])
                            (rf/dispatch [::events/set-extraction-pending true])
                            (@debounced-extract))}]
             (when (false? body-valid?)
               [:div.mt-1.flex.items-center.gap-1
                [bp/icon {:icon "warning-sign" :size 12 :intent "danger"}]
                [:span.text-xs.text-red-400 "Invalid JSON"]])]]
           ;; Right column: sentinel path substitution dropdowns
           [:div {:style {:flex "1"}}
            [:label.bp6-label "Substitutions"]
            (if (empty? sentinel-paths)
              [:p {:class "text-tn-fg-dim text-sm"} "No placeholders found."]
              (for [path sentinel-paths]
                (let [sel-id         (get substitutions path)
                      resolved-entry (when sel-id (find resolved-values path))
                      resolved-val   (when resolved-entry (val resolved-entry))
                      resolved-set?  (boolean resolved-entry)]
                  ^{:key path}
                  [:div.mb-3
                   [:code {:class "text-tn-cyan text-sm block mb-1"} path]
                   (if sel-id
                     [sel/searchable-select
                      {:items           sv-items
                       :selected-id     sel-id
                       :on-select       #(rf/dispatch [::events/set-substitution path %])
                       :on-clear        #(rf/dispatch [::events/set-substitution path nil])
                       :on-query-change [::events/set-shared-values-search]
                       :on-clear-search [::events/set-shared-values-search ""]
                       :placeholder     "Select shared value..."}]
                     [:div.flex.gap-1.items-center
                      [bp/icon {:icon "warning-sign" :intent "danger"}]
                      [sel/searchable-select
                       {:items           sv-items
                        :selected-id     nil
                        :on-select       #(rf/dispatch [::events/set-substitution path %])
                        :on-clear        nil
                        :on-query-change [::events/set-shared-values-search]
                        :on-clear-search [::events/set-shared-values-search ""]
                        :placeholder     "Select shared value..."}]])
                   (when sel-id
                     (cond
                       (and resolved-set? (some? resolved-val))
                       [:code {:class "text-xs block mt-1 text-tn-fg-muted"}
                        (js/JSON.stringify (clj->js (:value resolved-val)))]

                       (and resolved-set? (nil? resolved-val))
                       [:span {:class "text-xs text-tn-fg-dim block mt-1"}
                        "No value for this scope"]))])))]]
          (when error
            [error-banner/error-banner "Failed to create configuration." error])]
         [bp/dialog-footer
          {:actions
           (r/as-element
             [:<>
              [bp/button {:text     "Cancel"
                          :on-click #(rf/dispatch [::events/close-configuration-dialog])}]
              [bp/button {:text     "Create"
                          :intent   "primary"
                          :icon     "tick"
                          :loading  saving?
                          :disabled save-disabled?
                          :on-click #(rf/dispatch [::events/save-configuration])}]])}]]))
    (finally
      (deb/cancel-debounced-fn! debounced-extract))))

;; ---------------------------------------------------------------------------
;; Left sidebar — filter bar + config list
;; ---------------------------------------------------------------------------

(defn- config-sidebar []
  (let [{:keys [edges page-info selected-id selected filter-dimension-ids current-only]} @(rf/subscribe [::subs/configurations-page])
        dim-types  @(rf/subscribe [::subs/dimension-types])
        loading?   @(rf/subscribe [::subs/loading? :configurations])
        page-error @(rf/subscribe [::subs/error :configurations])]
    [:div {:class "w-72 shrink-0 border-r border-tn-border pr-3"}
     [:div.flex.items-center.justify-between.mb-3
      [:span.font-semibold.text-sm.text-tn-fg-muted "Configurations"]
      [:div.flex.items-center.gap-1
       [bp/button {:icon     "plus"
                   :minimal  true
                   :small    true
                   :on-click (fn []
                               (if selected
                                 (rf/dispatch [::events/open-configuration-dialog
                                               {:dimension-ids (mapv :id (:dimensions selected))
                                                :body-text     (js/JSON.stringify (clj->js (:body selected)) nil 2)
                                                :substitutions (into {} (map #(vector (:jsonpath %) (get-in % [:sharedValue :id])) (:substitutions selected)))}])
                                 (rf/dispatch [::events/open-configuration-dialog])))}]
       [bp/button {:icon     "refresh"
                   :minimal  true
                   :small    true
                   :loading  loading?
                   :on-click #(rf/dispatch [::events/fetch-configurations])}]]]

     ;; Filter dropdowns
     [:div.mb-2
      (doall (for [dt dim-types]
        (let [type-id (:id dt)
              items   @(rf/subscribe [::subs/dimensions-dropdown-items-no-base type-id])
              sel-id  (some (set (or filter-dimension-ids [])) (map :id items))]
          ^{:key type-id}
          [:div.mb-2
           [sel/searchable-select
            {:items            items
             :selected-id      sel-id
             :on-select        #(rf/dispatch [::events/set-config-filter-dimension %])
             :on-clear         (when sel-id
                                 #(rf/dispatch [::events/set-config-filter-dimension sel-id]))
             :on-query-change  [::events/search-dimensions-list type-id false]
             :on-clear-search  [::events/clear-dimensions-search-results type-id]
             :icon             "tag"
             :placeholder      (str "All " (:name dt) "s")}]])))]

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
             [:div.flex.items-center.justify-between.gap-2
              [:div.flex.items-center.gap-2.flex-wrap
               [dimensions-label/dimensions-label (:dimensions node)]
               (when (:isCurrent node)
                 [bp/tag {:intent "success" :minimal true} "current"])]
              (if (:isCurrent node)
                [bp/button {:icon     "trash"
                            :small    true
                            :intent   "danger"
                            :minimal  true
                            :on-click (fn [e]
                                        (.stopPropagation e)
                                        (rf/dispatch [::events/set-configuration-current (:id node) false]))}]
                [bp/button {:icon     "endorsed"
                            :small    true
                            :intent   "success"
                            :minimal  true
                            :on-click (fn [e]
                                        (.stopPropagation e)
                                        (rf/dispatch [::events/set-configuration-current (:id node) true]))}])]
             [timestamp/timestamp (:createdAt node)]]))
        [load-more/load-more-button
         {:has-next? (:hasNextPage page-info)
          :loading?  loading?
          :on-click  #(rf/dispatch [::events/load-more-configurations])}]])]))

;; ---------------------------------------------------------------------------
;; Right panel — configuration detail
;; ---------------------------------------------------------------------------

(defn- config-main []
  (let [{:keys [selected-id selected]} @(rf/subscribe [::subs/configurations-page])
        loading?   @(rf/subscribe [::subs/loading? :configuration-detail])]
    [:div.flex-1.pl-4
     (if-not selected-id
       [states/empty-state {:icon        "document"
                            :title       "Select a configuration"
                            :description "Choose a configuration from the left to view its details."}]
       [:<>
        [:div.flex.items-center.justify-between.mb-4
         [:h3.bp6-heading "Configuration Detail"]
         [:div.flex.items-center.gap-2
          [bp/button {:icon "cross" :minimal true
                      :on-click #(rf/dispatch [::events/select-configuration nil])}]]]

        (cond
          loading?
          [states/loading-spinner]

          (nil? selected)
          [:p.text-tn-fg-muted "Configuration not found."]

          :else
          [:div

           (if (some? (:projection selected))
             [monaco/monaco-diff-editor
              {:original (js/JSON.stringify (clj->js (:body selected)) nil 2)
               :modified (js/JSON.stringify (clj->js (:projection selected)) nil 2)
               :height   "420px"}]
             [:<>
              [:h5.bp6-heading.mb-2 "Body"]
              [json-block/json-block {:value (:body selected)}]])

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
  [:div {:class "max-w-7xl mx-auto px-4 py-4"}
   [:div.flex
    [config-sidebar]
    [config-main]]
   [configuration-dialog]])
