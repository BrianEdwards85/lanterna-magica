(ns lanterna-magica.views.outputs
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.components.dimensions-label :as dimensions-label]
   [lanterna-magica.components.error-banner :as error-banner]
   [lanterna-magica.components.inputs :as inputs]
   [lanterna-magica.components.json-block :as json-block]
   [lanterna-magica.components.multi-dimension-picker :as multi-dim-picker]
   [lanterna-magica.components.states :as states]
   [lanterna-magica.components.timestamp :as timestamp]
   [lanterna-magica.events :as events]
   [lanterna-magica.routes :as routes]
   [lanterna-magica.subs :as subs]
   [re-frame.core :as rf]
   [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Create Output Dialog
;; ---------------------------------------------------------------------------

(defn output-dialog []
  (let [{:keys [open? output]} @(rf/subscribe [::subs/output-dialog])
        saving? @(rf/subscribe [::subs/loading? :save-output])
        error   @(rf/subscribe [::subs/error :save-output])]
    (when open?
      [bp/dialog {:title    "New Output"
                  :icon     "export"
                  :is-open  true
                  :on-close #(rf/dispatch [::events/close-output-dialog])
                  :class    "w-full max-w-lg"}
       [bp/dialog-body
        [:div.mb-4
         [:label.bp6-label "Path Template"]
         [inputs/local-input {:value       (or (:pathTemplate output) "")
                              :placeholder "/data/{environment}/{service}.yml"
                              :on-change   #(rf/dispatch [::events/set-output-field :pathTemplate %])}]]
        [:div.mb-4
         [:label.bp6-label "Format"]
         [bp/html-select {:value     (or (:format output) "json")
                          :on-change (fn [e]
                                       (rf/dispatch [::events/set-output-field :format (.. e -target -value)]))}
          [:option {:value "json"} "JSON"]
          [:option {:value "yml"}  "YAML"]
          [:option {:value "toml"} "TOML"]
          [:option {:value "env"}  "ENV"]]]
        [:div.mb-4
         [:label.bp6-label "Dimensions"]
         [multi-dim-picker/multi-dimension-picker
          {:selected-ids (or (:dimensionIds output) [])
           :on-toggle    #(rf/dispatch [::events/toggle-output-dimension %])}]]
        (when error
          [error-banner/error-banner "Failed to create output." error])]
       [bp/dialog-footer
        {:actions
         (r/as-element
           [:<>
            [bp/button {:text     "Cancel"
                        :on-click #(rf/dispatch [::events/close-output-dialog])}]
            [bp/button {:text     "Save"
                        :intent   "primary"
                        :icon     "tick"
                        :loading  saving?
                        :on-click #(rf/dispatch [::events/save-output])}]])}]])))

;; ---------------------------------------------------------------------------
;; Output Card
;; ---------------------------------------------------------------------------

(defn- last-trigger-status [results]
  (if (seq results)
    (let [latest   (first (sort-by :writtenAt #(compare %2 %1) results))
          success? (:succeeded latest)]
      [:div.flex.items-center.gap-1
       [bp/icon {:icon   (if success? "tick-circle" "error")
                 :size   14
                 :intent (if success? "success" "danger")}]
       [:span {:class (str "text-xs " (if success? "text-green-400" "text-red-400"))}
        "Last run"]
       [timestamp/timestamp (:writtenAt latest)]])
    [:span.text-xs.text-tn-fg-dim "Never triggered"]))

(defn- output-card [node]
  (let [{:keys [id pathTemplate format dimensions results]} node
        triggering? @(rf/subscribe [::subs/loading? [:trigger-output id]])]
    [:div {:class "rounded p-4 bg-tn-bg-card flex flex-col gap-2"}
     ;; Header row: path template + action buttons
     [:div.flex.items-start.justify-between.gap-2
      [:a {:href  (routes/href :route/output {:id id})
           :class "font-mono text-sm text-tn-cyan hover:underline break-all"}
       pathTemplate]
      [:div.flex.items-center.gap-1.shrink-0
       [bp/button {:icon     "play"
                   :small    true
                   :intent   "primary"
                   :minimal  true
                   :loading  triggering?
                   :on-click #(rf/dispatch [::events/trigger-output id])}]
       [bp/button {:icon     "trash"
                   :small    true
                   :intent   "danger"
                   :minimal  true
                   :on-click #(rf/dispatch [::events/archive-output id])}]]]
     ;; Format badge + dimension tags
     [:div.flex.items-center.gap-2.flex-wrap
      [bp/tag {:minimal true :intent "primary"} (str format)]
      [dimensions-label/dimensions-label dimensions]]
     ;; Last trigger status
     [last-trigger-status (or results [])]]))

;; ---------------------------------------------------------------------------
;; Output Detail — result row
;; ---------------------------------------------------------------------------

(defn- result-row [result format]
  (r/with-let [expanded? (r/atom false)]
    (let [{:keys [path succeeded error content writtenAt]} result]
      [:div {:class "rounded bg-tn-bg-card mb-2"}
       ;; Header row
       [:div {:class    "flex items-center justify-between gap-2 px-3 py-2 cursor-pointer"
              :on-click #(swap! expanded? not)}
        [:div.flex.items-center.gap-2.min-w-0
         [bp/icon {:icon   (if succeeded "tick-circle" "error")
                   :size   14
                   :intent (if succeeded "success" "danger")}]
         [:span {:class "font-mono text-sm break-all"} path]]
        [:div.flex.items-center.gap-2.shrink-0
         (when writtenAt [timestamp/timestamp writtenAt])
         [bp/icon {:icon (if @expanded? "chevron-up" "chevron-down") :size 12}]]]
       ;; Error message (always visible when failed)
       (when (and (not succeeded) (seq error))
         [:div {:class "px-3 pb-2 text-xs text-red-400"}
          error])
       ;; Expanded content
       (when @expanded?
         [:div {:class "px-3 pb-3"}
          (if (and (= format "json") (seq content))
            (let [parsed (try (js/JSON.parse content) (catch :default _ nil))]
              (if parsed
                [json-block/json-block {:value (js->clj parsed :keywordize-keys false) :class "text-xs"}]
                [:pre {:class "text-xs whitespace-pre-wrap break-all"} content]))
            [:pre {:class "text-xs whitespace-pre-wrap break-all"} (or content "")])])])))

;; ---------------------------------------------------------------------------
;; Output Detail — page
;; ---------------------------------------------------------------------------

(defn output-detail []
  (let [output     @(rf/subscribe [::subs/selected-output])
        loading?   @(rf/subscribe [::subs/loading? :output-detail])
        triggering? (and output @(rf/subscribe [::subs/loading? [:trigger-output (:id output)]]))]
    (cond
      (and loading? (nil? output))
      [:div {:class "max-w-7xl mx-auto px-4 py-4"}
       [states/loading-spinner]]

      (nil? output)
      [:div {:class "max-w-7xl mx-auto px-4 py-4"}
       [states/empty-state {:icon        "export"
                            :title       "Output not found"
                            :description "The requested output could not be loaded."}]]

      :else
      (let [{:keys [id pathTemplate format dimensions results archivedAt]} output
            sorted-results (sort-by :path (or results []))]
        [:div {:class "max-w-7xl mx-auto px-4 py-4"}
         ;; Back link + page header
         [:div.flex.items-center.gap-2.mb-4
          [:a {:href  (routes/href :route/outputs)
               :class "text-tn-fg-dim hover:text-tn-fg text-sm flex items-center gap-1"}
           [bp/icon {:icon "arrow-left" :size 12}]
           "Outputs"]]

         [:div.flex.items-start.justify-between.gap-4.mb-4
          [:div.min-w-0
           [:h2 {:class "bp6-heading font-mono break-all"} pathTemplate]
           [:div.flex.items-center.gap-2.flex-wrap.mt-1
            [bp/tag {:minimal true :intent "primary"} (str format)]
            [dimensions-label/dimensions-label dimensions]
            (when (some? archivedAt)
              [bp/tag {:minimal true :intent "warning"} "Archived"])]]
          [:div.flex.items-center.gap-2.shrink-0
           [bp/button {:icon     "play"
                       :text     "Trigger"
                       :intent   "primary"
                       :loading  triggering?
                       :on-click #(rf/dispatch [::events/trigger-output id])}]
           [bp/button {:icon     "refresh"
                       :minimal  true
                       :loading  loading?
                       :on-click #(rf/dispatch [::events/load-output id])}]
           (when (nil? archivedAt)
             [bp/button {:icon     "trash"
                         :intent   "danger"
                         :minimal  true
                         :on-click #(rf/dispatch [::events/archive-output id])}])]]

         ;; Results panel
         [:h3 {:class "bp6-heading text-sm mb-3"}
          (str "Results (" (count sorted-results) ")")]

         (if (empty? sorted-results)
           [:div {:class "rounded bg-tn-bg-card px-4 py-6 text-center text-tn-fg-dim text-sm"}
            "No results yet — trigger this output to generate files."]
           [:div
            (for [result sorted-results]
              ^{:key (:id result)}
              [result-row result format])])]))))

;; ---------------------------------------------------------------------------
;; Screen
;; ---------------------------------------------------------------------------

(defn outputs-screen []
  (let [route-name @(rf/subscribe [::subs/current-route-name])]
    (if (= route-name :route/output)
      [output-detail]
      (let [{:keys [edges]} @(rf/subscribe [::subs/outputs-page])
            loading? @(rf/subscribe [::subs/loading? :outputs])
            error    @(rf/subscribe [::subs/error :outputs])]
        [:div {:class "max-w-7xl mx-auto px-4 py-4"}
         ;; Page header
         [:div.flex.items-center.justify-between.mb-4
          [:h2.bp6-heading "Outputs"]
          [:div.flex.items-center.gap-2
           [bp/button {:icon     "refresh"
                       :minimal  true
                       :loading  loading?
                       :on-click #(rf/dispatch [::events/fetch-outputs])}]
           [bp/button {:icon     "plus"
                       :text     "New Output"
                       :intent   "primary"
                       :on-click #(rf/dispatch [::events/open-output-dialog])}]]]

         (when error
           [error-banner/error-banner "Failed to load outputs." error])

         ;; Output list
         (cond
           (and loading? (empty? edges))
           [states/loading-spinner]

           (empty? edges)
           [states/empty-state {:icon        "export"
                                :title       "No outputs yet"
                                :description "Create an output to start writing configurations to disk."}]

           :else
           [:div {:class "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"}
            (for [edge edges]
              ^{:key (get-in edge [:node :id])}
              [output-card (:node edge)])])

         [output-dialog]]))))
