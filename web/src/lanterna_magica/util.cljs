(ns lanterna-magica.util)

;; ---------------------------------------------------------------------------
;; Date / time formatting
;; ---------------------------------------------------------------------------

(def ^:private day-names
  ["Sunday" "Monday" "Tuesday" "Wednesday" "Thursday" "Friday" "Saturday"])

(def ^:private month-names
  ["Jan" "Feb" "Mar" "Apr" "May" "Jun"
   "Jul" "Aug" "Sep" "Oct" "Nov" "Dec"])

(defn- pad2 [n]
  (if (< n 10) (str "0" n) (str n)))

(defn- format-time-12h [date]
  (let [h  (.getHours date)
        m  (.getMinutes date)
        ap (if (< h 12) "AM" "PM")
        h  (cond (zero? h) 12 (> h 12) (- h 12) :else h)]
    (str h ":" (pad2 m) " " ap)))

(defn- same-day? [a b]
  (and (= (.getFullYear a) (.getFullYear b))
       (= (.getMonth a) (.getMonth b))
       (= (.getDate a) (.getDate b))))

(defn- yesterday? [date now]
  (let [yesterday (doto (js/Date. (.getTime now))
                    (.setDate (- (.getDate now) 1)))]
    (same-day? date yesterday)))

(defn- days-ago [date now]
  (/ (- (.getTime now) (.getTime date)) 86400000))

(defn format-relative-time
  "Human-readable relative timestamp from an ISO date string."
  [iso-str]
  (let [date    (js/Date. iso-str)
        now     (js/Date.)
        diff-ms (- (.getTime now) (.getTime date))
        diff-s  (/ diff-ms 1000)
        diff-m  (/ diff-s 60)
        diff-h  (/ diff-m 60)]
    (cond
      (neg? diff-ms) "in the future"
      (< diff-m 1)   "just now"
      (< diff-h 1)   (str (js/Math.floor diff-m) "m ago")
      (and (same-day? date now) (< diff-h 12))
      (str (js/Math.floor diff-h) "h ago")

      (same-day? date now)
      (str "Today at " (format-time-12h date))

      (yesterday? date now)
      (str "Yesterday at " (format-time-12h date))

      (< (days-ago date now) 7)
      (str (nth day-names (.getDay date)) " at " (format-time-12h date))

      (= (.getFullYear date) (.getFullYear now))
      (str (nth month-names (.getMonth date)) " " (.getDate date))

      :else
      (str (nth month-names (.getMonth date)) " " (.getDate date) ", " (.getFullYear date)))))

(defn format-full-datetime
  "Full human-readable timestamp, e.g. 'Wednesday, Feb 19, 2026 at 3:42 PM'."
  [iso-str]
  (let [d (js/Date. iso-str)]
    (str (nth day-names (.getDay d)) ", "
         (nth month-names (.getMonth d)) " "
         (.getDate d) ", "
         (.getFullYear d) " at "
         (format-time-12h d))))
